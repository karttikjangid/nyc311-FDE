"""VALIDATE: the validation contract as code.

Every rule returns two severities, because validation depends on the decision (Class 6):
  reporting = is this safe for a weekly evidence report?
  live      = is this safe for answering one resident about one request right now?
Statuses: PASS / WARN / FAIL / UNKNOWN. A rule marked blocking stops publication when its
reporting status is FAIL. Rule text lives here and in docs/02_validation_contract.md.
"""
from datetime import date

import pandas as pd

RULES = {}


def rule(rule_id, name, assumption, blocking=False):
    def deco(fn):
        RULES[rule_id] = {"id": rule_id, "name": name, "assumption": assumption, "blocking": blocking, "fn": fn}
        return fn
    return deco


def _share(n, d):
    return round(n / d, 6) if d else None


def result(ctx, rule_id, value, denominator, reporting, live, evidence):
    r = RULES[rule_id]
    return {"id": rule_id, "name": r["name"], "assumption": r["assumption"], "blocking": r["blocking"],
            "value": value, "denominator": denominator, "reporting": reporting, "live": live, "evidence": evidence}


@rule("R01", "Retrieval count matches source count", "We received every row the source says exists.", blocking=True)
def r01(ctx):
    bad, drift = {}, {}
    for name, e in ctx["manifest"]["datasets"].items():
        if e.get("expected_count") is None or e["received_rows"] != e["expected_count"]:
            bad[name] = [e.get("expected_count"), e["received_rows"]]
        if e.get("count_after_pull") is not None and e["count_after_pull"] != e["expected_count"]:
            drift[name] = [e["expected_count"], e["count_after_pull"]]
    status = "FAIL" if bad else ("WARN" if drift else "PASS")
    return result(ctx, "R01", len(bad), len(ctx["manifest"]["datasets"]), status, status,
                  {"mismatch_expected_received": bad, "source_count_changed_during_pull": drift})


@rule("R02", "Raw files unchanged since retrieval", "Replayed bytes are the bytes the API returned.", blocking=True)
def r02(ctx):
    n = len(ctx["integrity"])
    s = "FAIL" if n else "PASS"
    return result(ctx, "R02", n, None, s, s, ctx["integrity"][:20])


@rule("R03", "Required columns present", "Every field the model needs exists in each source.", blocking=True)
def r03(ctx):
    missing = {name: [c for c in ctx["cfg"]["datasets"][name]["required"] if c not in df.columns]
               for name, df in ctx["frames"].items()}
    missing = {k: v for k, v in missing.items() if v}
    s = "FAIL" if missing else "PASS"
    return result(ctx, "R03", sum(len(v) for v in missing.values()), None, s, s, missing)


@rule("R04", "Full SLA hierarchy available", "Requests carry descriptor_2, the third level of the SLA key.")
def r04(ctx):
    ok = "descriptor_2" in ctx["frames"]["service_requests"].columns
    s = "PASS" if ok else "WARN"
    return result(ctx, "R04", int(ok), 1, s, s, "descriptor_2 present" if ok else
                  "descriptor_2 missing: SLA matched at detail level only; more AMBIGUOUS results")


@rule("R05", "One row per request", "unique_key identifies one request.", blocking=True)
def r05(ctx):
    rep = ctx["clean_report"]
    conflicts, exact = rep["conflicting_duplicate_keys"], rep["exact_duplicate_rows_removed"]
    s = "FAIL" if conflicts else ("WARN" if exact else "PASS")
    return result(ctx, "R05", conflicts, rep["rows_in"], s, s,
                  {"conflicting_duplicate_keys": conflicts, "exact_duplicate_rows_removed": exact})


@rule("R06", "Timestamps parse", "Date fields are valid ISO timestamps.", blocking=True)
def r06(ctx):
    rep, n = ctx["clean_report"], ctx["clean_report"]["rows_in"]
    bad = sum(v for k, v in rep.items() if k.endswith("_unparseable"))
    sh = _share(bad, n)
    s = "FAIL" if sh > ctx["cfg"]["thresholds"]["unparseable_date_share_fail"] else ("WARN" if bad else "PASS")
    return result(ctx, "R06", bad, n, s, s, {k: v for k, v in rep.items() if k.endswith("_unparseable")})


@rule("R07", "Rows inside the requested window", "The API filter returned only the cohort we asked for.", blocking=True)
def r07(ctx):
    sr, w = ctx["sr"], ctx["cfg"]["window"]
    out = int(((sr["created_ts"] < pd.Timestamp(w["created_from"])) | (sr["created_ts"] >= pd.Timestamp(w["created_to"]))).sum())
    s = "FAIL" if out else "PASS"
    return result(ctx, "R07", out, len(sr), s, s, w)


@rule("R08", "Snapshot fresh enough", "The snapshot is recent relative to the run date.", blocking=True)
def r08(ctx):
    age = (date.fromisoformat(ctx["run_date"]) - pd.Timestamp(ctx["as_of_utc"]).date()).days
    limit = ctx["cfg"]["thresholds"]["snapshot_max_age_days"]
    s = "FAIL" if age > limit or age < 0 else "PASS"
    return result(ctx, "R08", age, limit, s, "UNKNOWN",
                  {"snapshot_age_days": age, "max_age_days": limit,
                   "live_note": "Open data publication lag vs the 311 system is not measurable from this source."})


def _row_rule(ctx, rule_id, mask, fail_key, evidence_extra=None):
    sr = ctx["sr"]
    n, d = int(mask.sum()), len(sr)
    sh = _share(n, d)
    rep = "PASS" if n == 0 else ("FAIL" if sh > ctx["cfg"]["thresholds"][fail_key] else "WARN")
    live = "PASS" if n == 0 else "FAIL"
    ev = {"rows": n, "share": sh, "by_agency": sr.loc[mask, "agency"].value_counts().head(8).to_dict()}
    if evidence_extra:
        ev.update(evidence_extra)
    return result(ctx, rule_id, n, d, rep, live, ev)


@rule("R09", "Event order is possible", "No request is closed or updated before it was created.")
def r09(ctx):
    sr = ctx["sr"]
    m = sr["flag_closed_before_created"] | sr["flag_action_before_created"]
    return _row_rule(ctx, "R09", m, "chronology_bad_share_fail_reporting",
                     {"closed_before_created": int(sr["flag_closed_before_created"].sum()),
                      "action_before_created": int(sr["flag_action_before_created"].sum()),
                      "not_counted_date_only_same_day": {
                          "closed": int(sr["flag_closed_date_only_same_day"].sum()),
                          "last_action": int(sr["flag_action_date_only_same_day"].sum()),
                          "by_agency": sr.loc[sr["flag_closed_date_only_same_day"] | sr["flag_action_date_only_same_day"], "agency"].value_counts().to_dict(),
                          "why": "timestamp is 00:00:00 on the creation date: date-only precision, reported under R11"}})


@rule("R10", "Status and closed date agree", "Closed requests have a closed date; others do not.")
def r10(ctx):
    return _row_rule(ctx, "R10", ctx["sr"]["flag_status_date_conflict"], "status_conflict_share_fail_reporting")


@rule("R11", "Closure time has hour precision", "closed_date carries a real time of day.")
def r11(ctx):
    sr = ctx["sr"]
    closed = sr["closed_ts"].notna()
    by = sr[closed].groupby("agency")["flag_midnight_close"].mean().round(4)
    heavy = by[by > 0.5].to_dict()
    n = int(sr["flag_midnight_close"].sum())
    same_day = int((sr["flag_closed_date_only_same_day"] | sr["flag_action_date_only_same_day"]).sum())
    s = "WARN" if heavy or same_day else "PASS"
    return result(ctx, "R11", n, int(closed.sum()), s, s,
                  {"agencies_over_50pct_midnight_closures": heavy,
                   "date_only_timestamps_earlier_than_creation_same_day": same_day,
                   "action": "exclude these agencies from hour-level durations; do not treat as ordering errors"})


@rule("R12", "No timestamps after the snapshot", "Nothing happened after the data was pulled.")
def r12(ctx):
    n = int(ctx["sr"]["flag_future_date"].sum())
    return result(ctx, "R12", n, len(ctx["sr"]), "WARN" if n else "PASS", "FAIL" if n else "PASS", {"rows": n})


@rule("R13", "Status values are known", "Status uses the documented set of values.")
def r13(ctx):
    vc = ctx["sr"]["status"].value_counts(dropna=False)
    unknown = {str(k): int(v) for k, v in vc.items() if k not in ctx["cfg"]["status_values_known"]}
    s = "WARN" if unknown else "PASS"
    return result(ctx, "R13", sum(unknown.values()), len(ctx["sr"]), s, "FAIL" if unknown else "PASS",
                  {"unknown_values": unknown, "observed": {str(k): int(v) for k, v in vc.items()}})


@rule("R14", "Closing note present", "Every request has a note a resident could be shown.")
def r14(ctx):
    return _row_rule(ctx, "R14", ctx["sr"]["flag_note_missing"], "null_note_share_fail_reporting",
                     {"by_status": ctx["sr"].loc[ctx["sr"]["flag_note_missing"], "status"].value_counts().to_dict()})


@rule("R15", "Closing note text intact", "Notes are complete and correctly encoded.")
def r15(ctx):
    sr = ctx["sr"]
    m = sr["flag_note_mojibake"] | sr["flag_note_truncated_500"]
    n = int(m.sum())
    return result(ctx, "R15", n, len(sr), "WARN" if n else "PASS", "FAIL" if n else "PASS",
                  {"mojibake_rows": int(sr["flag_note_mojibake"].sum()),
                   "truncated_at_500_chars_rows": int(sr["flag_note_truncated_500"].sum()),
                   "truncation_rule": "length exactly 500 and last character not sentence punctuation (heuristic)"})


@rule("R16", "Mapping file is valid", "Every code in the closing-text mapping is an allowed value.", blocking=True)
def r16(ctx):
    info = ctx["mapping_info"]
    n = len(info["invalid_values"]) + info["duplicate_hashes"]
    s = "FAIL" if n else "PASS"
    return result(ctx, "R16", n, info["rows"], s, s, info)


@rule("R17", "Mapping covers the focus-agency notes", "Coded notes cover almost all focus-agency requests.", blocking=True)
def r17(ctx):
    sr = ctx["sr"]
    dd = sr[sr["agency"].isin(ctx["cfg"]["deep_dive_agencies"]) & ~sr["flag_note_missing"]]
    covered = int(dd["note_hash"].isin(set(ctx["mapping"]["text_sha256_16"])).sum())
    sh = _share(covered, len(dd))
    t = ctx["cfg"]["thresholds"]
    s = "PASS" if sh >= t["mapping_coverage_pass"] else ("WARN" if sh >= t["mapping_coverage_fail"] else "FAIL")
    by = dd.assign(m=dd["note_hash"].isin(set(ctx["mapping"]["text_sha256_16"]))).groupby("agency")["m"].mean().round(4).to_dict()
    return result(ctx, "R17", covered, len(dd), s, s, {"coverage": sh, "by_agency": by,
                  "unmapped_rows_are": "UNKNOWN in the KPI, never dropped"})


@rule("R18", "Mapping agrees with an independent coder", "A second coder reads the notes the same way.")
def r18(ctx):
    ag = ctx["agreement"]
    if ag is None:
        return result(ctx, "R18", None, None, "UNKNOWN", "UNKNOWN", "coder 2 file not present yet")
    kappas = {f: v["cohen_kappa_strings"] for f, v in ag["fields"].items()}
    low = min(k for k in kappas.values() if k is not None)
    s = "PASS" if low >= ctx["cfg"]["thresholds"]["kappa_pass"] else "WARN"
    return result(ctx, "R18", low, ag["strings_both"], s, "UNKNOWN",
                  {"kappa_by_field": kappas, "live_note": "Needs agency sign-off before any resident-facing use."})


@rule("R19", "SLA units understood", "Every SLA value is a number of hours or days, or the known sentinel.")
def r19(ctx):
    rules_ = ctx["sla_rules"]
    bad = rules_.loc[~rules_["unit_parsed"], "sla_days"].value_counts().to_dict()
    n = int((~rules_["unit_parsed"]).sum())
    s = "WARN" if n else "PASS"
    return result(ctx, "R19", n, len(rules_), s, s, {"unparsed_values": {str(k): int(v) for k, v in bad.items()},
                  "assumption": "days = calendar days x 24h (UNVERIFIED)"})


@rule("R20", "SLA reference is current", "The response targets still apply to requests in this cohort.")
def r20(ctx):
    upd = ctx["manifest"]["datasets"]["sla"].get("rows_updated_at_utc")
    age = (pd.Timestamp(ctx["as_of_utc"]) - pd.Timestamp(upd)).days if upd else None
    warn = age is None or age > ctx["cfg"]["thresholds"]["sla_age_days_warn"]
    return result(ctx, "R20", age, None, "WARN" if warn else "PASS", "FAIL" if warn else "PASS",
                  {"sla_rows_updated_at_utc": upd, "age_days_at_snapshot": age})


@rule("R21", "SLA match is unambiguous", "Each request maps to at most one response target.")
def r21(ctx):
    st = ctx["sla_match"]["sla_state"].value_counts().to_dict()
    amb = int(st.get("AMBIGUOUS", 0))
    return result(ctx, "R21", amb, len(ctx["sla_match"]), "WARN" if amb else "PASS", "WARN" if amb else "PASS",
                  {"states": {k: int(v) for k, v in st.items()}})


@rule("R22", "Joins do not duplicate rows", "Adding SLA and mapping keeps one row per request.", blocking=True)
def r22(ctx):
    ok = ctx["joined_rows"] == len(ctx["sr"])
    s = "PASS" if ok else "FAIL"
    return result(ctx, "R22", ctx["joined_rows"], len(ctx["sr"]), s, s, "row count before vs after joins")


@rule("R23", "Timezone of timestamps", "Floating timestamps are America/New_York local time.")
def r23(ctx):
    return result(ctx, "R23", None, None, "UNKNOWN", "UNKNOWN",
                  {"assumed": ctx["cfg"]["timezone_assumed"], "basis": "hour-of-day pattern only; publisher does not state it"})


@rule("R24", "Status calls attributable to an agency", "Call-center rows can be linked to an agency or request.")
def r24(ctx):
    cc = ctx["frames"]["call_center"]
    n = int(cc["agency"].isna().sum()) if "agency" in cc else len(cc)
    s = "WARN" if n else "PASS"
    return result(ctx, "R24", n, len(cc), s, s, {"agency_null_rows": n, "use": "context only; no request key exists"})


@rule("R25", "Survey represents all requests", "Survey answers describe requests in general.")
def r25(ctx):
    return result(ctx, "R25", len(ctx["frames"]["survey"]), None, "WARN", "FAIL",
                  "Self-selected respondents who gave contact info; month = response month; no request key. Context only.")


def run_rules(ctx, ids=None):
    return [RULES[i]["fn"](ctx) for i in (ids or sorted(RULES))]


def reconcile(model_counts, sr_rows):
    """R26, run after the model is built."""
    ok = all(v == sr_rows for v in model_counts.values())
    s = "PASS" if ok else "FAIL"
    return {"id": "R26", "name": "Model reconciles to cleaned rows", "blocking": True,
            "assumption": "Every request appears exactly once in each request-grain table.",
            "value": model_counts, "denominator": sr_rows, "reporting": s, "live": s, "evidence": "row counts per table"}


def gate(results):
    blocking = [r["id"] for r in results if r["blocking"] and r["reporting"] == "FAIL"]
    live_fail = [r["id"] for r in results if r["live"] in ("FAIL", "UNKNOWN")]
    return {
        "publish": not blocking,
        "blocking_failures": blocking,
        "reporting_gate": "NOT READY" if blocking else "READY (with warnings)" if any(r["reporting"] == "WARN" for r in results) else "READY",
        "live_answer_gate": "NOT READY" if live_fail else "READY",
        "live_answer_blockers": live_fail,
    }
