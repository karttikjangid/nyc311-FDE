"""TRANSFORM/MODEL: reorganise source-shaped data around the request workflow in SQLite.

Tables (grain in brackets):
  service_request [request]           entity + record-quality flags
  request_event   [request x event]   created / last_action / closed / due, from timestamps
  closing_note    [distinct note]     coded meaning of each closing text (mapping version)
  response_target [request]           SLA match state and hours
  sla_rule        [SLA rule]          reference table as published
  status_calls_daily [day x topic]    call-center interaction context (no request key)
  survey_stratum  [agency x type x response month]  resident view, context only
  run_context     [key]               as-of time, deep-dive agencies, mapping version
Views/tables built by sql/model.sql: agency_action, closure_outcome, answerability.
"""
import sqlite3
from pathlib import Path

import pandas as pd

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"
FLAGS = ["flag_closed_before_created", "flag_action_before_created", "flag_closed_date_only_same_day",
         "flag_action_date_only_same_day", "flag_status_date_conflict",
         "flag_midnight_close", "flag_future_date", "flag_note_missing", "flag_note_mojibake", "flag_note_truncated_500"]


def _ts(s):
    return s.dt.strftime("%Y-%m-%d %H:%M:%S").where(s.notna(), None)


def build(db_path, sr, sla_rules, sla_match, mapping, calls, survey, as_of_local_ts, cfg, mapping_version):
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    cols = ["unique_key", "agency", "agency_name", "complaint_type", "descriptor", "status",
            "open_data_channel_type", "borough", "note_hash"]
    t = sr[cols].copy()
    t["descriptor_2"] = sr["descriptor_2"] if "descriptor_2" in sr else None
    for c in ["created_ts", "closed_ts", "last_action_ts", "due_ts"]:
        t[c] = _ts(sr[c])
    for f in FLAGS:
        t[f] = sr[f].astype(int)
    t.to_sql("service_request", con, index=False, chunksize=50000)

    con.execute("""CREATE TABLE request_event AS
        SELECT unique_key, 'created' AS event_type, created_ts AS event_ts, 'created_date' AS source_field FROM service_request WHERE created_ts IS NOT NULL
        UNION ALL SELECT unique_key, 'last_action', last_action_ts, 'resolution_action_updated_date' FROM service_request WHERE last_action_ts IS NOT NULL
        UNION ALL SELECT unique_key, 'closed', closed_ts, 'closed_date' FROM service_request WHERE closed_ts IS NOT NULL
        UNION ALL SELECT unique_key, 'due', due_ts, 'due_date' FROM service_request WHERE due_ts IS NOT NULL""")
    del t

    m = mapping.rename(columns={"text_sha256_16": "note_hash"}).copy()
    m["mapping_version"] = mapping_version
    m.drop(columns=["text"]).to_sql("closing_note", con, index=False)

    sla_rules[["agency", "problem", "problem_details", "additional_details", "sla_days", "hours"]].to_sql("sla_rule", con, index=False)
    sla_match.to_sql("response_target", con, index=False, chunksize=100000)

    c = calls.assign(call_date=calls["call_ts"].dt.strftime("%Y-%m-%d"))
    c.groupby(["call_date", "inquiry_name"], dropna=False).size().rename("calls").reset_index() \
        .to_sql("status_calls_daily", con, index=False)

    s = survey.assign(complaint_type_norm=survey["complaint_type"].str.strip().str.lower())
    s["disagree"] = s["overall_satisfaction"].isin(["Disagree", "Strongly Disagree"]).astype(int)
    reason = s["dissatisfaction_reason"].fillna("")
    s["reason_status_updates"] = reason.str.contains("status update", case=False).astype(int)
    s["reason_not_corrected"] = reason.str.startswith("The Agency did not correct the issue").astype(int)
    s.groupby(["agency", "complaint_type_norm", "year_i", "month_i"], dropna=False).agg(
        responses=("unique_key", "size"), disagree=("disagree", "sum"),
        reason_status_updates=("reason_status_updates", "sum"), reason_not_corrected=("reason_not_corrected", "sum"),
    ).reset_index().rename(columns={"year_i": "year", "month_i": "month"}).to_sql("survey_stratum", con, index=False)

    ctx = [("as_of_local", as_of_local_ts.strftime("%Y-%m-%d %H:%M:%S")), ("mapping_version", mapping_version),
           ("long_open_days", str(cfg["thresholds"]["long_open_days"]))]
    ctx += [("deep_dive_agency", a) for a in cfg["deep_dive_agencies"]]
    pd.DataFrame(ctx, columns=["key", "value"]).to_sql("run_context", con, index=False)

    con.execute("CREATE UNIQUE INDEX ix_sr ON service_request(unique_key)")
    con.execute("CREATE INDEX ix_sr_note ON service_request(note_hash)")
    con.execute("CREATE UNIQUE INDEX ix_rt ON response_target(unique_key)")
    con.executescript((SQL_DIR / "model.sql").read_text())
    con.commit()
    return con


def request_grain_counts(con):
    q = {t: f"SELECT COUNT(*), COUNT(DISTINCT unique_key) FROM {t}" for t in ["service_request", "response_target", "answerability"]}
    out = {}
    for t, sql in q.items():
        n, d = con.execute(sql).fetchone()
        out[t] = n if n == d else -1  # -1 marks duplicated keys
    return out
