"""METRICS: run the SQL in sql/metrics/ against the model and build the evidence table."""
import json
from pathlib import Path

import pandas as pd

METRIC_SQL = Path(__file__).resolve().parents[1] / "sql" / "metrics"

OWNER = {
    "A1": "Agency + OTI (event timestamps)",
    "A2": "Agency + OTI (status sync)",
    "A3": "Agency (closing-note wording)",
    "A4": "311 + agency (response targets)",
    "A5": "Agency + OTI (publish status in 311, not a separate site)",
}


def run_all(con):
    return {p.stem: pd.read_sql_query(p.read_text(), con) for p in sorted(METRIC_SQL.glob("*.sql"))}


def overall(con):
    q = """SELECT COUNT(*) AS requests,
                  ROUND(AVG(result='ANSWERABLE'),4) AS answerable_share,
                  ROUND(AVG(result='UNKNOWN'),4) AS unknown_share,
                  ROUND(AVG(result='FAIL'),4) AS fail_share,
                  ROUND(AVG(result_strict='ANSWERABLE'),4) AS answerable_share_strict
           FROM answerability WHERE deep = 1"""
    return pd.read_sql_query(q, con).iloc[0].to_dict()


def evidence_table(t):
    kpi = t["kpi_by_agency"]
    kpi = kpi[kpi["deep_dive"] == 1].copy()
    g = t["guardrail_closed_without_fix"].set_index("agency")
    n = t["open_next_step"].set_index("agency")
    lo = t["long_open"].set_index("agency")
    bl = t["blockers"]
    rows = []
    for _, r in kpi.iterrows():
        a = r["agency"]
        b = bl[bl["agency"] == a].sort_values("requests", ascending=False)
        blk = b["primary_blocker"].iloc[0] if len(b) else None
        blk_share = round(float(b["requests"].iloc[0]) / float(r["requests"]), 4) if len(b) else 0.0
        rows.append({
            "agency": a, "requests": int(r["requests"]),
            "kpi_answerable": r["answerable_share"], "kpi_answerable_strict": r["answerable_share_strict"],
            "kpi_unknown": r["unknown_share"], "kpi_fail": r["fail_share"],
            "guardrail_closed_without_fix_evidence": g.loc[a, "closed_without_fix_evidence"] if a in g.index else None,
            "open_next_step_rate": n.loc[a, "next_step_rate"] if a in n.index else None,
            "open_requests": int(n.loc[a, "open_requests"]) if a in n.index else 0,
            "open_longer_than_7d": lo.loc[a, "share_open_longer_than_n_days"] if a in lo.index else None,
            "main_blocker": blk, "main_blocker_share_of_requests": blk_share, "fix_owner": OWNER.get(blk, "n/a"),
        })
    return pd.DataFrame(rows)


def _pct(x):
    return "n/a" if x is None or pd.isna(x) else f"{100 * float(x):.1f}%"


def evidence_markdown(ev, ov, status_calls_total, as_of_local, snapshot_id, mapping_version, by_type=None):
    lines = [
        "# Evidence table",
        "",
        f"Snapshot `{snapshot_id}`, as-of time {as_of_local} (America/New_York, assumed). Cohort: requests created 2026-04-01 to 2026-06-30. Mapping {mapping_version}.",
        "",
        f"**Project KPI, focus agencies (HPD, NYPD, DOT, DOB) combined:** {_pct(ov['answerable_share'])} of {int(ov['requests']):,} requests pass all five record checks "
        f"({_pct(ov['answerable_share_strict'])} under the strict reading). {_pct(ov['unknown_share'])} are UNKNOWN, {_pct(ov['fail_share'])} FAIL.",
        "",
        "| Agency | Requests | KPI: answerable | KPI strict | UNKNOWN | FAIL | Guardrail: Closed without fix evidence | Open: next step stated | Open > 7 days | Main blocker (share of all requests) | Owner of the fix |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, r in ev.iterrows():
        lines.append(f"| {r['agency']} | {r['requests']:,} | {_pct(r['kpi_answerable'])} | {_pct(r['kpi_answerable_strict'])} | {_pct(r['kpi_unknown'])} | "
                     f"{_pct(r['kpi_fail'])} | {_pct(r['guardrail_closed_without_fix_evidence'])} | {_pct(r['open_next_step_rate'])} "
                     f"(of {r['open_requests']:,}) | {_pct(r['open_longer_than_7d'])} | {r['main_blocker']} ({_pct(r['main_blocker_share_of_requests'])}) | {r['fix_owner']} |")
    if by_type is not None and len(by_type):
        lines += ["", "## Proposed decision by complaint type (strict reading; types with 500+ requests)", "",
                  "| Agency | Complaint type | Requests | Answerable (strict) | Answerable (loose) | Main blocker (strict) | Proposed decision | Decision if notes read loosely |",
                  "|---|---|---:|---:|---:|---|---|---|"]
        order = {"hold": 0, "fix blocker first": 1, "candidate for measurement pilot": 2}
        bt = by_type.assign(o=by_type["proposed_decision"].map(order)).sort_values(["o", "requests"], ascending=[True, False])
        for _, r in bt.iterrows():
            blk = f"{r['main_blocker']} ({_pct(r['main_blocker_share'])})" if isinstance(r["main_blocker"], str) else "none"
            lines.append(f"| {r['agency']} | {r['complaint_type']} | {int(r['requests']):,} | {_pct(r['answerable_share_strict'])} | "
                         f"{_pct(r['answerable_share'])} | {blk} | {r['proposed_decision']} | {r['decision_if_loose_reading']} |")
    lines += ["", f"Context: {status_calls_total:,} agent-handled \"Service Request Status\" calls in the same weeks (undercounted by the publisher's own note; no agency or request key).",
              "", "Checks: A1 chronology, A2 status/date agree, A3 closing note readable (closed: says what happened; open: says who acts next), A4 open requests have a published 311 response target, A5 status is not held in another system.",
              "Strict reading: medium-certainty note codes count as UNKNOWN."]
    return "\n".join(lines) + "\n"


def to_jsonable(obj):
    return json.loads(pd.io.json.dumps(obj, double_precision=6)) if not isinstance(obj, (dict, list)) else obj
