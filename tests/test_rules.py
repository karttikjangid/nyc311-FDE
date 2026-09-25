import pandas as pd

from pipeline import clean, mapping, sla
from tests.conftest import build_rows

AS_OF = pd.Timestamp("2026-09-25 07:00:00")


def cleaned():
    return clean.clean_service_requests(pd.DataFrame(build_rows()), AS_OF)


def test_flags_known_problems_without_changing_values():
    raw = pd.DataFrame(build_rows())
    df, rep = clean.clean_service_requests(raw, AS_OF)
    row = df.set_index("unique_key")
    assert bool(row.loc["3000", "flag_closed_before_created"])            # real ordering error
    assert not bool(row.loc["3001", "flag_closed_before_created"])        # 00:00 on the same day is precision, not error
    assert bool(row.loc["3001", "flag_closed_date_only_same_day"])
    assert bool(row.loc["3002", "flag_status_date_conflict"])             # Assigned but has a closed date
    assert bool(row.loc["3003", "flag_note_missing"])
    assert (df["closed_date"].fillna("") == raw["closed_date"].fillna("")).all()   # originals untouched


def test_exact_duplicates_removed_conflicts_reported():
    raw = pd.DataFrame(build_rows())
    dup = pd.concat([raw, raw.head(2)], ignore_index=True)
    _, rep = clean.clean_service_requests(dup, AS_OF)
    assert rep["exact_duplicate_rows_removed"] == 2 and rep["conflicting_duplicate_keys"] == 0
    conflict = raw.head(1).copy()
    conflict["status"] = "Open"
    _, rep = clean.clean_service_requests(pd.concat([raw, conflict], ignore_index=True), AS_OF)
    assert rep["conflicting_duplicate_keys"] == 1


def test_sla_states():
    rules = sla.prepare_rules(pd.DataFrame([
        {"agency": "A", "problem": "P", "problem_details": "D", "additional_details": "X", "sla_days": "4 days"},
        {"agency": "A", "problem": "P", "problem_details": "D", "additional_details": "Y", "sla_days": "8 hours"},
        {"agency": "A", "problem": "Q", "problem_details": "E", "additional_details": "N/A", "sla_days": "SLA Not Managed by 311"},
        {"agency": "A", "problem": "R", "problem_details": "F", "additional_details": "N/A", "sla_days": "2 days"},
    ]))
    req = pd.DataFrame({"unique_key": list("12345"), "agency_name": ["a"] * 5,
                        "complaint_type": ["P", "P", "Q", "R", "Z"], "descriptor": ["D", "D", "E", "other", "D"],
                        "descriptor_2": ["X", "", "", "", ""]})
    m = sla.match(req, rules).set_index("unique_key")
    assert m.loc["1", "sla_state"] == "MATCHED" and m.loc["1", "sla_hours"] == 96   # full hierarchy resolves it
    assert m.loc["2", "sla_state"] == "AMBIGUOUS"                                     # two values, no third level
    assert m.loc["3", "sla_state"] == "NOT_MANAGED_BY_311"
    assert m.loc["4", "sla_state"] == "MATCHED"        # no detail rule, but every rule under A+R agrees
    assert m.loc["5", "sla_state"] == "UNMATCHED"
    assert sla.parse_sla_hours("8 hours") == 8 and sla.parse_sla_hours("banana") is None


def test_mapping_file_is_valid_and_kappa_is_correct():
    m, info = mapping.load_mapping(mapping.Path(__file__).resolve().parents[1] / "reference" / "closing_text_map_v2.csv")
    assert info["invalid_values"] == [] and info["duplicate_hashes"] == 0
    assert mapping.cohen_kappa(list("aabb"), list("aabb")) == 1.0
    assert round(mapping.cohen_kappa(list("aabb"), list("abab")), 4) == 0.0
