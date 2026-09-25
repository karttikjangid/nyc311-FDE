import json
import re
from pathlib import Path

from pipeline import extract
from pipeline.config import load_config


class FakeSocrata:
    """Answers metadata, count(*) and keyset-paged row queries for one in-memory dataset."""

    def __init__(self, rows, fail_first_page_once=False):
        self.rows, self.queries, self.fail_once = rows, [], fail_first_page_once

    def get(self, url, params=None, timeout=None):
        from tests.test_http import Resp
        if url.endswith(".json") and "/api/views/" in url:
            cols = [{"fieldName": k} for k in self.rows[0]]
            return Resp(200, json.dumps({"columns": cols, "rowsUpdatedAt": 1790300423}).encode())
        params = params or {}
        if params.get("$select", "").startswith("count"):
            return Resp(200, json.dumps([{"count": str(len(self.rows))}]).encode())
        self.queries.append(dict(params))
        if self.fail_once:
            self.fail_once = False
            return Resp(500)
        m = re.search(r"unique_key > '([^']*)'", params.get("$where", ""))
        rows = [r for r in self.rows if not m or r["unique_key"] > m.group(1)]
        rows = sorted(rows, key=lambda r: r["unique_key"])[: int(params["$limit"])]
        return Resp(200, json.dumps(rows).encode())


def small_cfg(tmp_path):
    cfg = load_config()
    cfg["page_size"] = 2
    cfg["http"]["backoff_base_s"] = 0
    cfg["paths"]["snapshots"] = str(tmp_path)
    return cfg


def test_keyset_pagination_collects_every_row(tmp_path):
    rows = [{"unique_key": k, "created_date": "2026-04-01T00:00:00.000"} for k in ["a1", "a2", "a3", "a4", "a5"]]
    fake = FakeSocrata(rows, fail_first_page_once=True)
    entry = extract.pull_dataset(fake, small_cfg(tmp_path), "service_requests", tmp_path / "sr")
    assert entry["received_rows"] == entry["expected_count"] == 5
    assert entry["method"] == "keyset" and entry["duplicate_keys_seen"] == 0
    assert [f["rows"] for f in entry["files"]] == [2, 2, 1]
    assert "unique_key > 'a2'" in fake.queries[-2]["$where"]      # page 3 continues after the last key of page 2
    assert all("$offset" not in q for q in fake.queries)
    assert entry["fields_missing_in_source"]                      # config asks for columns the fake lacks: recorded, not fatal


def test_tampered_page_is_detected(workspace):
    tmp, cfg_path = workspace
    cfg = load_config(cfg_path)
    snap = extract.latest_snapshot_id(cfg)
    page = Path(cfg["paths"]["snapshots"]) / snap / "sla" / "page_00001.json.gz"
    page.write_bytes(page.read_bytes() + b"\0")
    _, _, integrity = extract.load_snapshot(cfg, snap)
    assert any(i["problem"] == "sha256 mismatch" for i in integrity)


def test_partial_snapshot_is_never_used(workspace):
    tmp, cfg_path = workspace
    cfg = load_config(cfg_path)
    (Path(cfg["paths"]["snapshots"]) / "29990101T000000Z.partial").mkdir()
    assert not extract.latest_snapshot_id(cfg).endswith(".partial")
