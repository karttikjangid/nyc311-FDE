"""Shared fixtures: a tiny, hand-built snapshot with known problems, plus a config that points at tmp paths."""
import csv
import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.extract import sha256_file  # noqa: E402

MAPPING = ROOT / "reference" / "closing_text_map_v2.csv"


def mapped_texts():
    rows = list(csv.DictReader(open(MAPPING, encoding="utf-8")))
    by = {}
    for r in rows:
        by.setdefault(r["agency"], []).append(r["text"])
    return by


def sr_row(key, agency, created, closed, status, note, ctype="HEAT/HOT WATER", descriptor="ENTIRE BUILDING", last=None):
    names = {"HPD": "Department of Housing Preservation and Development", "NYPD": "New York City Police Department",
             "DOT": "Department of Transportation", "DOB": "Department of Buildings"}
    r = {"unique_key": key, "created_date": created, "agency": agency, "agency_name": names[agency],
         "complaint_type": ctype, "descriptor": descriptor, "status": status, "open_data_channel_type": "ONLINE",
         "borough": "BROOKLYN", "resolution_action_updated_date": last or closed or created}
    if closed:
        r["closed_date"] = closed
    if note is not None:
        r["resolution_description"] = note
    return r


def build_rows():
    t = mapped_texts()
    rows = []
    for i in range(30):
        rows.append(sr_row(f"{1000 + i}", "NYPD", "2026-04-02T10:00:00.000", "2026-04-02T11:00:00.000", "Closed",
                           t["NYPD"][i % 5], ctype="Noise - Residential", descriptor="Loud Music/Party"))
    for i in range(20):
        rows.append(sr_row(f"{2000 + i}", "HPD", "2026-05-01T09:00:00.000", "2026-05-03T09:00:00.000", "Closed", t["HPD"][i % 6]))
    rows.append(sr_row("3000", "DOT", "2026-06-01T09:00:00.000", "2026-05-01T09:00:00.000", "Closed", t["DOT"][0],
                       ctype="Street Condition", descriptor="Pothole"))            # closed before created -> A1 FAIL
    rows.append(sr_row("3001", "DOB", "2026-06-01T09:00:00.000", "2026-06-01T00:00:00.000", "Closed", t["DOB"][0],
                       ctype="General Construction/Plumbing", descriptor="Contrary To LL 58/87"))  # date-only same day
    rows.append(sr_row("3002", "DOB", "2026-06-02T09:00:00.000", "2026-06-03T00:00:00.000", "Assigned", t["DOB"][0]))  # status conflict
    rows.append(sr_row("3003", "HPD", "2026-06-05T09:00:00.000", None, "Open", None))                     # note missing
    return rows


def write_snapshot(root, snap_id="20260925T000000Z", rows=None, as_of="2026-09-25T11:00:00+00:00"):
    rows = rows if rows is not None else build_rows()
    datasets = {
        "service_requests": rows,
        "call_center": [{"unique_id": str(i), "date": "2026-04-06T00:00:00.000", "date_time": "2026-04-06T10:00:00.000",
                         "inquiry_name": "Service Request Status" if i % 2 else "Noise from Neighbor"} for i in range(10)],
        "sla": [{"agency": "Department of Housing Preservation and Development", "problem": "HEAT/HOT WATER",
                 "problem_details": "ENTIRE BUILDING", "additional_details": "N/A", "sla_days": "4 days"},
                {"agency": "Department of Buildings", "problem": "General Construction/Plumbing",
                 "problem_details": "N/A", "additional_details": "N/A", "sla_days": "SLA Not Managed by 311"}],
        "survey": [{"unique_key": str(i), "agency": "HPD", "complaint_type": "Heat/Hot Water", "year": "2026", "month": "5",
                    "overall_satisfaction": "Strongly Disagree" if i % 2 else "Agree",
                    "dissatisfaction_reason": "The Agency did not correct the issue." if i % 2 else None} for i in range(6)],
    }
    snap = Path(root) / snap_id
    manifest = {"snapshot_id": snap_id, "as_of_utc": as_of, "datasets": {}}
    for name, data in datasets.items():
        d = snap / name
        d.mkdir(parents=True)
        p = d / "page_00001.json.gz"
        with open(p, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
            gz.write(json.dumps(data).encode())
        (d / "metadata_views.json").write_text(json.dumps({"columns": [{"fieldName": k} for k in data[0]]}))
        manifest["datasets"][name] = {"dataset_id": name, "expected_count": len(data), "received_rows": len(data),
                                      "count_after_pull": len(data), "rows_updated_at_utc": "2026-09-24T00:00:00+00:00"
                                      if name != "sla" else "2024-03-05T20:10:53+00:00",
                                      "metadata_file": f"{name}/metadata_views.json",
                                      "files": [{"path": f"{name}/page_00001.json.gz", "rows": len(data), "sha256": sha256_file(p)}]}
    (snap / "manifest.json").write_text(json.dumps(manifest))
    return snap


@pytest.fixture
def workspace(tmp_path):
    cfg = json.loads((ROOT / "config" / "pipeline.json").read_text())
    cfg["paths"] = {"snapshots": str(tmp_path / "snapshots"), "output": str(tmp_path / "output"),
                    "logs": str(tmp_path / "logs"), "mapping": str(MAPPING), "mapping_blind_coder1": str(MAPPING),
                    "coder2": str(tmp_path / "no_coder2.csv")}
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))
    write_snapshot(tmp_path / "snapshots")
    return tmp_path, cfg_path
