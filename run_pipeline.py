#!/usr/bin/env python3
"""NYC 311 record-answerability pipeline.

  python run_pipeline.py --run-date 2026-09-26                      # replay latest saved snapshot (offline)
  python run_pipeline.py --run-date 2026-09-26 --source live        # pull a new snapshot from the API first
  python run_pipeline.py --run-date 2026-09-26 --chaos missing_column

EXTRACT -> VALIDATE -> CLEAN -> TRANSFORM/MODEL -> METRICS -> SAVE, with logging.
A blocking validation failure publishes nothing and leaves the previous output in place.
"""
import argparse
import json
import logging
import shutil
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

from pipeline import chaos, clean, extract, mapping, metrics, model, save, sla, validate
from pipeline.config import load_config, path
from pipeline.logging_utils import setup_logging

log = logging.getLogger("pipeline")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-date", required=True, help="logical run date, YYYY-MM-DD (output partition key)")
    ap.add_argument("--source", choices=["snapshot", "live"], default="snapshot")
    ap.add_argument("--snapshot-id", help="replay this snapshot (default: latest complete one)")
    ap.add_argument("--chaos", choices=chaos.CHAOS, help="inject a controlled failure")
    ap.add_argument("--config", help="alternative config file (tests)")
    ap.add_argument("--keep-model", action="store_true", help="keep model.sqlite (about 600 MB) in the output partition")
    return ap.parse_args(argv)


def run(args):
    date.fromisoformat(args.run_date)
    cfg = load_config(args.config) if args.config else load_config()
    setup_logging(path(cfg, "logs"), args.run_date)
    t0 = time.time()
    log.info("START run_date=%s source=%s chaos=%s", args.run_date, args.source, args.chaos)

    # EXTRACT
    if args.source == "live":
        session = requests.Session()
        import os
        if os.environ.get("SOCRATA_APP_TOKEN"):
            session.headers["X-App-Token"] = os.environ["SOCRATA_APP_TOKEN"]
        snapshot_id = extract.live_snapshot(session, cfg)
    else:
        snapshot_id = args.snapshot_id or extract.latest_snapshot_id(cfg)
    frames, manifest, integrity = extract.load_snapshot(cfg, snapshot_id)
    log.info("EXTRACT snapshot=%s rows=%s integrity_problems=%d", snapshot_id,
             {k: len(v) for k, v in frames.items()}, len(integrity))
    if args.chaos:
        frames, manifest = chaos.apply(args.chaos, frames, manifest)
        log.warning("CHAOS applied: %s", args.chaos)

    ctx = {"cfg": cfg, "frames": frames, "manifest": manifest, "integrity": integrity,
           "run_date": args.run_date, "as_of_utc": manifest["as_of_utc"]}
    results = validate.run_rules(ctx, ["R01", "R02", "R03"])
    if any(r["blocking"] and r["reporting"] == "FAIL" for r in results):
        return fail(cfg, args, snapshot_id, results, "structural checks failed before cleaning")

    # CLEAN
    as_of_local = clean.as_of_local(manifest["as_of_utc"], cfg["timezone_assumed"])
    sr, clean_report = clean.clean_service_requests(frames["service_requests"], as_of_local)
    calls = clean.clean_call_center(frames["call_center"])
    survey = clean.clean_survey(frames["survey"])
    log.info("CLEAN %s", clean_report)

    # TRANSFORM inputs: SLA match + mapping
    rules = sla.prepare_rules(frames["sla"])
    sla_match = sla.match(sr.drop_duplicates("unique_key"), rules)
    mp, mp_info = mapping.load_mapping(Path(cfg["_root"]) / cfg["paths"]["mapping"])
    # Agreement is measured on the blind comparison (coder 1 v1 vs coder 2), before adjudication.
    blind_v1, _ = mapping.load_mapping(Path(cfg["_root"]) / cfg["paths"].get("mapping_blind_coder1", cfg["paths"]["mapping"]))
    agreement = mapping.agreement(blind_v1, Path(cfg["_root"]) / cfg["paths"]["coder2"])
    # Row count a left join would produce: extra rows appear only if a join key repeats on the right side.
    sla_extra = int(sla_match["unique_key"].duplicated().sum())
    map_counts = mp["text_sha256_16"].value_counts()
    map_extra = int((sr["note_hash"].map(map_counts).fillna(1) - 1).clip(lower=0).sum())
    joined_rows = len(sr) + sla_extra + map_extra
    ctx.update({"sr": sr, "clean_report": clean_report, "sla_rules": rules, "sla_match": sla_match,
                "mapping": mp, "mapping_info": mp_info, "agreement": agreement, "joined_rows": joined_rows})
    results += validate.run_rules(ctx, [r for r in sorted(validate.RULES) if r not in ("R01", "R02", "R03")])
    for r in results:
        log.info("VALIDATE %s %-45s reporting=%-7s live=%s", r["id"], r["name"], r["reporting"], r["live"])
    if any(r["blocking"] and r["reporting"] == "FAIL" for r in results):
        return fail(cfg, args, snapshot_id, results, "blocking validation failure")

    # MODEL
    out_root = path(cfg, "output")
    final_dir = out_root / f"run_date={args.run_date}"
    tmp_dir = out_root / f".tmp_run_date={args.run_date}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    mapping_version = Path(cfg["paths"]["mapping"]).stem
    # Build the SQLite model on local disk (fast, and safe on network or synced folders), not in the output folder.
    import tempfile
    work_dir = Path(tempfile.mkdtemp(prefix="nyc311_model_"))
    db_path = work_dir / "model.sqlite"
    con = model.build(db_path, sr, rules, sla_match, mp, calls, survey, as_of_local, cfg, mapping_version)
    results.append(validate.reconcile(model.request_grain_counts(con), len(sr)))
    if results[-1]["reporting"] == "FAIL":
        con.close()
        shutil.rmtree(tmp_dir)
        shutil.rmtree(work_dir, ignore_errors=True)
        return fail(cfg, args, snapshot_id, results, "model does not reconcile to cleaned rows")

    # METRICS
    tables = metrics.run_all(con)
    ov = metrics.overall(con)
    # A small, deterministic slice of the request-grain model for readers without the database.
    import pandas as _pd
    _pd.read_sql_query("""SELECT a.*, sr.created_ts, sr.closed_ts, sr.last_action_ts, cn.action, cn.violation_finding,
                                 cn.fix_evidence, cn.next_step, cn.redirects_elsewhere, cn.certainty, rt.sla_state, rt.sla_hours
                          FROM answerability a JOIN service_request sr USING (unique_key)
                          LEFT JOIN closing_note cn ON cn.note_hash = sr.note_hash
                          LEFT JOIN response_target rt USING (unique_key)
                          WHERE a.deep = 1 AND (CAST(a.unique_key AS INTEGER) % 500) = 0
                          ORDER BY a.unique_key""", con).to_csv(tmp_dir / "request_journey_sample.csv", index=False)
    con.close()
    ev = metrics.evidence_table(tables)
    status_calls_total = int(tables["status_calls_weekly"]["status_calls"].sum())
    for name, df in tables.items():
        df.to_csv(tmp_dir / f"{name}.csv", index=False)
    ev.to_csv(tmp_dir / "evidence_table.csv", index=False)
    (tmp_dir / "evidence_table.md").write_text(metrics.evidence_markdown(
        ev, ov, status_calls_total, as_of_local.strftime("%Y-%m-%d %H:%M:%S"), snapshot_id, mapping_version, tables["kpi_by_complaint_type"]), encoding="utf-8")
    g = validate.gate(results)
    run_meta = {"run_date": args.run_date, "snapshot_id": snapshot_id, "as_of_utc": manifest["as_of_utc"],
                "as_of_local_assumed": as_of_local.strftime("%Y-%m-%d %H:%M:%S"), "chaos": args.chaos, "mapping_version": mapping_version}
    save.dump_json(tmp_dir / "validation_report.json", {"run": run_meta, "gate": g, "rules": results, "clean": clean_report})
    save.dump_json(tmp_dir / "metrics.json", {
        "run": run_meta,
        "project_kpi": {"name": "record-answerability proxy at as-of time", "deep_dive_overall": ov,
                        "by_agency": tables["kpi_by_agency"].to_dict(orient="records")},
        "supporting": {"intervention_mix": tables["intervention_mix"].to_dict(orient="records"),
                       "open_next_step": tables["open_next_step"].to_dict(orient="records"),
                       "status_calls_weekly": tables["status_calls_weekly"].to_dict(orient="records")},
        "guardrail": tables["guardrail_closed_without_fix"].to_dict(orient="records"),
        "coder_agreement": agreement,
    })
    (tmp_dir / "gate2.md").write_text(gate2_markdown(run_meta, g, results), encoding="utf-8")

    # SAVE
    if args.keep_model:
        shutil.move(str(db_path), tmp_dir / "model.sqlite")
    shutil.rmtree(work_dir, ignore_errors=True)
    save.publish(tmp_dir, final_dir)
    log.info("PUBLISHED %s gate=%s live_gate=%s in %.1fs", final_dir, g["reporting_gate"], g["live_answer_gate"], time.time() - t0)
    return 0


def fail(cfg, args, snapshot_id, results, reason):
    logs = path(cfg, "logs")
    p = logs / f"failed_run_{args.run_date}{'_' + args.chaos if args.chaos else ''}.json"
    save.dump_json(p, {"run_date": args.run_date, "snapshot_id": snapshot_id, "chaos": args.chaos, "reason": reason,
                       "gate": validate.gate(results), "rules": results})
    for r in results:
        if r["blocking"] and r["reporting"] == "FAIL":
            log.error("BLOCKING FAIL %s %s evidence=%s", r["id"], r["name"], json.dumps(r["evidence"], default=str)[:600])
    log.error("NOT PUBLISHED (%s). Previous output left unchanged. Details: %s", reason, p)
    return 2


def gate2_markdown(run_meta, g, results):
    rows = "\n".join(f"| {r['id']} | {r['name']} | {r['reporting']} | {r['live']} | {'yes' if r['blocking'] else 'no'} |" for r in results)
    return f"""# Gate 2: data readiness (generated)

Run date {run_meta['run_date']}, snapshot `{run_meta['snapshot_id']}`, as-of {run_meta['as_of_local_assumed']} (assumed America/New_York).

| Decision | Result |
|---|---|
| Weekly evidence reporting | **{g['reporting_gate']}** |
| Live answers to residents | **{g['live_answer_gate']}** (blocked by {', '.join(g['live_answer_blockers'])}) |

| Rule | Check | Weekly reporting | Live answer | Blocking |
|---|---|---|---|---|
{rows}

Pipeline behaviour evidenced in this run: raw pages verified by SHA-256 (R02), counts reconciled (R01, R26),
joins checked for fan-out (R22), output written to a temp folder and swapped in atomically.
"""


if __name__ == "__main__":
    sys.exit(run(parse_args()))
