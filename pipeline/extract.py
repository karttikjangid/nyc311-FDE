"""EXTRACT: pull raw pages from the NYC Open Data (Socrata) API, or replay a saved snapshot.

Live mode writes an immutable snapshot:
  data/raw/snapshots/<snapshot_id>/<dataset>/page_00001.json.gz ...
  data/raw/snapshots/<snapshot_id>/<dataset>/metadata_views.json
  data/raw/snapshots/<snapshot_id>/manifest.json   (written last)
The folder is built as <snapshot_id>.partial and renamed only after every dataset succeeded,
so a failed pull never looks like a usable snapshot.
"""
import gzip
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .config import path
from .http import get_json

log = logging.getLogger("extract")


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_gz(p, raw_bytes):
    # mtime=0 keeps the gzip bytes deterministic for identical content.
    with open(p, "xb") as f:
        with gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
            gz.write(raw_bytes)


def _quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def _where(ds_cfg, cfg):
    w = ds_cfg.get("where")
    return w.format(**cfg["window"]) if w else None


def pull_dataset(session, cfg, name, out_dir):
    """Pull one dataset with keyset pagination. Returns its manifest entry."""
    ds = cfg["datasets"][name]
    base = cfg["socrata_base"]
    out_dir.mkdir(parents=True, exist_ok=True)
    started = utc_now()

    meta, meta_raw = get_json(session, f"{base}/api/views/{ds['id']}.json", None, cfg["http"])
    (out_dir / "metadata_views.json").write_bytes(meta_raw)
    available = [c["fieldName"] for c in meta.get("columns", [])]
    wanted = ds["fields"] or available
    missing = [f for f in wanted if f not in available]
    fields = [f for f in wanted if f in available]
    if missing:
        log.warning("%s: columns not in source metadata, skipped: %s", name, missing)

    where = _where(ds, cfg)
    count_params = {"$select": "count(*) as count"}
    if where:
        count_params["$where"] = where
    count_rows, _ = get_json(session, f"{base}/resource/{ds['id']}.json", count_params, cfg["http"])
    expected = int(count_rows[0]["count"])
    log.info("%s: expected rows %d", name, expected)

    key = ds["key"]
    keyset = not key.startswith(":")  # system fields such as :id are paged by offset instead
    limit = cfg["page_size"]
    files, last_key, offset, page_no, seen, dup = [], None, 0, 1, set(), 0
    while True:
        params = {"$order": key, "$limit": limit}
        if ds["fields"]:
            params["$select"] = ",".join(fields)
        clauses = [c for c in (where, f"{key} > {_quote(last_key)}" if keyset and last_key is not None else None) if c]
        if clauses:
            params["$where"] = " AND ".join(f"({c})" for c in clauses)
        if not keyset:
            params["$offset"] = offset
        rows, raw = get_json(session, f"{base}/resource/{ds['id']}.json", params, cfg["http"])
        if not isinstance(rows, list):
            raise RuntimeError(f"{name}: page {page_no} is not a JSON array")
        p = out_dir / f"page_{page_no:05d}.json.gz"
        _write_gz(p, raw)
        if keyset:
            for r in rows:
                k = r.get(key)
                dup += k in seen
                seen.add(k)
        files.append({"path": None, "file": p.name, "rows": len(rows), "sha256": sha256_file(p),
                      "first_key": rows[0].get(key) if rows and keyset else None,
                      "last_key": rows[-1].get(key) if rows and keyset else None})
        log.info("%s: page %d rows=%d cumulative=%d", name, page_no, len(rows), sum(f["rows"] for f in files))
        if len(rows) < limit:
            break
        last_key = rows[-1].get(key)
        offset += limit
        page_no += 1

    recount, _ = get_json(session, f"{base}/resource/{ds['id']}.json", count_params, cfg["http"])
    received = sum(f["rows"] for f in files)
    return {
        "dataset_id": ds["id"], "method": "keyset" if keyset else "offset", "key": key,
        "where": where, "fields_requested": wanted, "fields_missing_in_source": missing,
        "expected_count": expected, "count_after_pull": int(recount[0]["count"]),
        "received_rows": received, "duplicate_keys_seen": dup if keyset else None,
        "pull_start_utc": started, "pull_end_utc": utc_now(),
        "rows_updated_at_utc": datetime.fromtimestamp(meta["rowsUpdatedAt"], timezone.utc).isoformat()
        if isinstance(meta.get("rowsUpdatedAt"), (int, float)) else None,
        "metadata_file": "metadata_views.json", "files": files,
    }


def live_snapshot(session, cfg):
    snap_root = path(cfg, "snapshots")
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    partial = snap_root / f"{snapshot_id}.partial"
    partial.mkdir(parents=True, exist_ok=False)
    manifest = {"snapshot_id": snapshot_id, "created_by": "pipeline/extract.py live", "datasets": {}}
    for name in ("service_requests", "call_center", "sla", "survey"):
        entry = pull_dataset(session, cfg, name, partial / name)
        for f in entry["files"]:
            f["path"] = f"{name}/{f.pop('file')}"
        entry["metadata_file"] = f"{name}/metadata_views.json"
        manifest["datasets"][name] = entry
    manifest["as_of_utc"] = manifest["datasets"]["service_requests"]["pull_start_utc"]
    (partial / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    final = snap_root / snapshot_id
    os.rename(partial, final)
    log.info("snapshot complete: %s", final)
    return snapshot_id


def latest_snapshot_id(cfg):
    root = path(cfg, "snapshots")
    ids = sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.endswith(".partial")
                 and (p / "manifest.json").exists()) if root.exists() else []
    if not ids:
        raise FileNotFoundError(f"no complete snapshot under {root}")
    return ids[-1]


KEEP_COLUMNS = {
    # Only the columns the pipeline uses are kept in memory; raw files keep everything.
    "call_center": ["unique_id", "date", "date_time", "agency", "inquiry_name", "call_resolution"],
    "survey": ["unique_key", "agency", "complaint_type", "descriptor", "year", "month",
               "overall_satisfaction", "dissatisfaction_reason"],
}
HIGH_CARDINALITY = {"unique_key", "unique_id", "created_date", "closed_date", "due_date",
                    "resolution_action_updated_date", "date_time", "time", "incident_zip"}


def _page_frame(page, keep, caches):
    df = pd.DataFrame(page)
    if keep:
        df = df.reindex(columns=[c for c in keep if c in df.columns])
    for col in df.columns:
        if col in HIGH_CARDINALITY:
            continue
        cache = caches.setdefault(col, {})
        # Share one str object per distinct value: 969k copies of the same note cost one.
        df[col] = [cache.setdefault(v, v) if isinstance(v, str) else None for v in df[col]]
    return df


def load_snapshot(cfg, snapshot_id):
    """Read a snapshot back. Never raises on content problems: they are returned for VALIDATE."""
    snap_dir = path(cfg, "snapshots") / snapshot_id
    manifest = json.loads((snap_dir / "manifest.json").read_text())
    root = Path(cfg["_root"])
    frames, integrity = {}, []
    for name, entry in manifest["datasets"].items():
        parts, caches = [], {}
        for f in entry["files"]:
            fp = (snap_dir / f["path"]) if not f["path"].startswith("@root/") else root / f["path"][6:]
            if not fp.exists():
                integrity.append({"dataset": name, "file": f["path"], "problem": "missing file"})
                continue
            if sha256_file(fp) != f["sha256"]:
                integrity.append({"dataset": name, "file": f["path"], "problem": "sha256 mismatch"})
            page = json.loads(gzip.decompress(fp.read_bytes()))
            if len(page) != f["rows"]:
                integrity.append({"dataset": name, "file": f["path"], "problem": f"rows {len(page)} != manifest {f['rows']}"})
            parts.append(_page_frame(page, KEEP_COLUMNS.get(name), caches))
            del page
        frames[name] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        meta_file = entry.get("metadata_file")
        if meta_file:
            mp = (snap_dir / meta_file) if not meta_file.startswith("@root/") else root / meta_file[6:]
            entry["_metadata_columns"] = [c["fieldName"] for c in json.loads(mp.read_text()).get("columns", [])] if mp.exists() else None
    return frames, manifest, integrity
