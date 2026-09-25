"""Closing-text mapping: load, check allowed values, and measure agreement with a second coder."""
from pathlib import Path

import pandas as pd

ALLOWED = {
    "action": {"inspected", "responded", "reviewed", "contacted", "no_access", "violation_issued", "summons_issued",
               "arrest", "work_order", "repaired", "referred", "duplicate", "not_jurisdiction", "owner_notified",
               "received_only", "redirect", "admin_closed", "insufficient_info", "other"},
    "violation_finding": {"violation", "no_violation", "condition_confirmed", "not_determined", "not_applicable"},
    "fix_evidence": {"yes", "partial", "no", "unknown"},
    "next_step": {"agency", "other_party", "resident", "none"},
    "redirects_elsewhere": {"yes", "partial", "no"},
    "certainty": {"high", "medium", "low"},
}
FIELDS = list(ALLOWED)


def load_mapping(p):
    m = pd.read_csv(p, dtype=str, keep_default_na=False)
    bad = []
    for f, allowed in ALLOWED.items():
        for h, v in zip(m["text_sha256_16"], m[f]):
            if v not in allowed:
                bad.append({"hash": h, "field": f, "value": v})
    dup = m["text_sha256_16"].duplicated().sum()
    return m, {"invalid_values": bad, "duplicate_hashes": int(dup), "rows": int(len(m))}


def cohen_kappa(a, b):
    a, b = list(a), list(b)
    n = len(a)
    if n == 0:
        return None
    cats = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def agreement(mapping, coder2_path, weights=None):
    """Per-field agreement between coder 1 (mapping) and coder 2. None if coder 2 file is absent."""
    if not Path(coder2_path).exists():
        return None
    c2 = pd.read_csv(coder2_path, dtype=str, keep_default_na=False)
    j = mapping.merge(c2, on="text_sha256_16", suffixes=("_c1", "_c2"), how="outer", indicator=True)
    result = {"strings_coder1": int(len(mapping)), "strings_coder2": int(len(c2)),
              "strings_both": int((j["_merge"] == "both").sum()), "fields": {}, "disagreements": []}
    both = j[j["_merge"] == "both"]
    w = pd.to_numeric(both["rows_in_2026Q2"], errors="coerce").fillna(0) if "rows_in_2026Q2" in both else None
    for f in FIELDS:
        x, y = both[f + "_c1"], both[f + "_c2"]
        same = (x == y)
        result["fields"][f] = {
            "percent_agreement_strings": round(float(same.mean()), 4) if len(both) else None,
            "percent_agreement_rows": round(float((same * w).sum() / w.sum()), 4) if w is not None and w.sum() else None,
            "cohen_kappa_strings": round(cohen_kappa(x, y), 4) if len(both) else None,
        }
        for _, r in both[~same].iterrows():
            result["disagreements"].append({"hash": r["text_sha256_16"], "field": f, "coder1": r[f + "_c1"],
                                            "coder2": r[f + "_c2"], "rows": r.get("rows_in_2026Q2")})
    return result
