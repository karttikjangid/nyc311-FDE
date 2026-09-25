"""Match each request to the published 311 response target (cs9t-e3x8).

The SLA is 'the amount of time the Agency needs to address the request' (dataset metadata). It is a
2024 reference, not a repair date. Matching is exact text after lower-casing and trimming; no fuzzy match.

States:
  MATCHED              one numeric target found at the most specific level available
  NOT_MANAGED_BY_311   the only target found is the sentinel "SLA Not Managed by 311"
  AMBIGUOUS            candidate rows disagree on the target
  UNMATCHED            no rule for this agency + problem
A coarser key (agency + problem) is used only when no detail-level rule exists AND every rule under it
has the same value.
"""
import re

import pandas as pd

SENTINEL = "sla not managed by 311"


def norm(s):
    return s.fillna("").astype(str).str.strip().str.lower()


def parse_sla_hours(text):
    """'4 days' -> 96.0, '8 hours' -> 8.0, sentinel -> None. Days assumed calendar (UNVERIFIED)."""
    if not isinstance(text, str):
        return None
    t = text.strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(day|days|hour|hours)", t)
    if not m:
        return None
    n = float(m.group(1))
    return n * 24 if m.group(2).startswith("day") else n


def prepare_rules(sla_raw):
    r = sla_raw.copy()
    for c in ["agency", "problem", "problem_details", "additional_details", "sla_days"]:
        if c not in r:
            r[c] = pd.NA
    r["a"], r["p"] = norm(r["agency"]), norm(r["problem"])
    r["d"], r["dd"] = norm(r["problem_details"]), norm(r["additional_details"])
    r["value"] = norm(r["sla_days"])
    r["hours"] = r["sla_days"].map(parse_sla_hours)
    r["unit_parsed"] = r["hours"].notna() | r["value"].eq(SENTINEL)
    return r


def _resolve(values):
    vals = sorted(set(values))
    if not vals:
        return "UNMATCHED", None
    if len(vals) > 1:
        return "AMBIGUOUS", None
    return ("NOT_MANAGED_BY_311", None) if vals[0] == SENTINEL else ("MATCHED", vals[0])


def match(requests, rules):
    """Return a frame keyed by unique_key with sla_state, sla_value, sla_hours."""
    req = pd.DataFrame({
        "unique_key": requests["unique_key"],
        "a": norm(requests["agency_name"]), "p": norm(requests["complaint_type"]),
        "d": norm(requests["descriptor"]),
        "dd": norm(requests["descriptor_2"]) if "descriptor_2" in requests else pd.Series("", index=requests.index),
    })
    has_dd = "descriptor_2" in requests
    by_ap = rules.groupby(["a", "p"])
    ap_groups = {k: g for k, g in by_ap}
    combos = req[["a", "p", "d", "dd"]].drop_duplicates()
    out = []
    for a, p, d, dd in combos.itertuples(index=False):
        g = ap_groups.get((a, p))
        if g is None:
            state, value = "UNMATCHED", None
        else:
            gd = g[g["d"] == d]
            if len(gd):
                if has_dd and dd:
                    gdd = gd[gd["dd"] == dd]
                    gd = gdd if len(gdd) else gd
                state, value = _resolve(gd["value"])
            else:
                state, value = _resolve(g["value"])
        out.append((a, p, d, dd, state, value))
    res = pd.DataFrame(out, columns=["a", "p", "d", "dd", "sla_state", "sla_value"])
    res["sla_hours"] = res["sla_value"].map(parse_sla_hours)
    merged = req.merge(res, on=["a", "p", "d", "dd"], how="left", validate="many_to_one")
    return merged[["unique_key", "sla_state", "sla_value", "sla_hours"]]
