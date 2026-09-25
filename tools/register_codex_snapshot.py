"""Register the first acquisition (done by acquire/acquire.py with offset paging) as a pipeline snapshot.

No raw file is copied or changed. The manifest points at the existing files ("@root/" = project root)
and records their SHA-256 so later runs can prove the bytes are unchanged.
Run once:  python tools/register_codex_snapshot.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.extract import sha256_file  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SNAP_ID = "20260925T112431Z_initial"

SOURCES = {
    "service_requests": ("erm2-nwe9", RAW / "service_requests" / "created_2026Q2", RAW / "metadata" / "erm2-nwe9_views.json", "unique_key"),
    "call_center": ("wewp-mm3p", RAW / "related" / "wewp-mm3p" / "created_2026Q2", RAW / "related" / "wewp-mm3p" / "metadata_views.json", "unique_id"),
    "sla": ("cs9t-e3x8", RAW / "related" / "cs9t-e3x8" / "full", RAW / "related" / "cs9t-e3x8" / "metadata_views.json", ":id"),
    "survey": ("5ijn-vbdv", RAW / "related" / "5ijn-vbdv" / "year_gte_2025", RAW / "related" / "5ijn-vbdv" / "metadata_views.json", "unique_key"),
}


def rel(p):
    return "@root/" + str(p.relative_to(ROOT))


def main():
    import gzip
    manifest = {"snapshot_id": SNAP_ID, "created_by": "acquire/acquire.py (offset paging), registered by tools/register_codex_snapshot.py", "datasets": {}}
    for name, (ds_id, folder, meta_path, key) in SOURCES.items():
        src = json.loads((folder / "_manifest.json").read_text())
        meta = json.loads(meta_path.read_text())
        files = []
        for p in sorted(folder.glob("page_*.json.gz")):
            rows = len(json.loads(gzip.decompress(p.read_bytes())))
            files.append({"path": rel(p), "rows": rows, "sha256": sha256_file(p)})
        fields = sorted({k for p in sorted(folder.glob("page_*.json.gz"))[:1] for r in json.loads(gzip.decompress(p.read_bytes()))[:1000] for k in r})
        manifest["datasets"][name] = {
            "dataset_id": ds_id, "method": "offset", "key": key,
            "expected_count": src.get("expected_count"), "received_rows": sum(f["rows"] for f in files),
            "count_after_pull": None,
            "pull_start_utc": src.get("pull_start_utc"), "pull_end_utc": src.get("pull_end_utc"),
            "rows_updated_at_utc": datetime.fromtimestamp(meta["rowsUpdatedAt"], timezone.utc).isoformat(),
            "fields_seen_in_first_page": fields,
            "fields_missing_in_source": [],
            "metadata_file": rel(meta_path), "files": files,
            "source_manifest": rel(folder / "_manifest.json"),
        }
    manifest["as_of_utc"] = manifest["datasets"]["service_requests"]["pull_start_utc"]
    out = ROOT / "data" / "raw" / "snapshots" / SNAP_ID
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("registered", out)


if __name__ == "__main__":
    main()
