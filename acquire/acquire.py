#!/usr/bin/env python3
"""Acquire immutable NYC 311 API responses; run stages independently."""

import argparse
import csv
import gzip
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
BASE = "https://data.cityofnewyork.us"
CATALOG = "https://api.us.socrata.com/api/catalog/v1"
DATASET = "erm2-nwe9"
START = "2026-04-01T00:00:00"
END = "2026-07-01T00:00:00"
LIMIT = 50000
FIELDS = [
    "unique_key", "created_date", "closed_date", "due_date",
    "resolution_action_updated_date", "agency", "agency_name",
    "complaint_type", "descriptor", "status", "resolution_description",
    "open_data_channel_type", "borough", "community_board",
    "incident_zip", "location_type",
]
RETRIABLE = {429, 500, 502, 503, 504}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def setup_log():
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    path = ROOT / "logs" / ("acquire_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s UTC %(levelname)s %(message)s",
        handlers=[logging.FileHandler(path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.Formatter.converter = time.gmtime
    logging.info("Run started; log=%s", path)
    return path


def status_path():
    REPORTS.mkdir(parents=True, exist_ok=True)
    return REPORTS / "acquisition_status.json"


def load_status():
    path = status_path()
    return json.loads(path.read_text()) if path.exists() else {"problems": [], "steps": {}}


def save_status(status):
    status_path().write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n")


def problem(status, step, message, path=None):
    item = {"step": step, "message": str(message), "path": str(path) if path else None, "time_utc": utc_now()}
    status["problems"].append(item)
    logging.error("PROBLEM %s: %s; path=%s", step, message, path)
    save_status(status)


def request(session, url, params=None):
    for attempt in range(6):
        try:
            response = session.get(url, params=params, timeout=(20, 180))
        except requests.Timeout as exc:
            if attempt == 5:
                raise RuntimeError(f"timeout after 5 retries: {exc}") from exc
            delay = 2 ** (attempt + 1)
            logging.warning("RETRY timeout attempt=%d delay=%ds url=%s params=%s", attempt + 1, delay, url, params)
            time.sleep(delay)
            continue
        if response.status_code in RETRIABLE:
            if attempt == 5:
                raise RuntimeError(f"HTTP {response.status_code} after 5 retries: {response.text[:4000]}")
            delay = 2 ** (attempt + 1)
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        delay = max(delay, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                    except (TypeError, ValueError):
                        logging.warning("Unparseable Retry-After: %r", retry_after)
            logging.warning("RETRY HTTP %d attempt=%d delay=%.1fs Retry-After=%r url=%s params=%s", response.status_code, attempt + 1, delay, retry_after, url, params)
            time.sleep(delay)
            continue
        if response.status_code >= 400:
            logging.error("HTTP %d body=%s url=%s params=%s", response.status_code, response.text[:10000], url, params)
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:4000]}")
        return response.content
    raise AssertionError("unreachable")


def save_raw(path, data, gzip_page=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        logging.info("Existing raw file retained unchanged: %s", path)
        return path.read_bytes() if not gzip_page else gzip.decompress(path.read_bytes())
    # Exclusive creation prevents overwriting even if another run starts concurrently.
    with path.open("xb") as out:
        if gzip_page:
            with gzip.GzipFile(filename="", mode="wb", fileobj=out) as gz:
                gz.write(data)
        else:
            out.write(data)
    logging.info("Saved raw response: %s bytes=%d", path, len(data))
    return data


def get_raw(session, url, path, params=None, gzip_page=False):
    if path.exists():
        return save_raw(path, b"", gzip_page)
    return save_raw(path, request(session, url, params), gzip_page)


def metadata(session, status, dataset=DATASET):
    path = RAW / "metadata" / f"{dataset}_views.json" if dataset == DATASET else RAW / "related" / dataset / "metadata_views.json"
    try:
        meta = json.loads(get_raw(session, f"{BASE}/api/views/{dataset}.json", path))
        if meta.get("id") != dataset:
            raise ValueError(f"dataset id mismatch: requested {dataset}, received {meta.get('id')}")
        if dataset == DATASET:
            columns_path = RAW / "metadata" / f"{dataset}_columns.csv"
            if not columns_path.exists():
                with columns_path.open("x", newline="", encoding="utf-8") as out:
                    writer = csv.writer(out)
                    writer.writerow(["fieldName", "name", "dataTypeName", "description"])
                    for col in meta.get("columns", []):
                        writer.writerow([col.get(key, "") for key in ("fieldName", "name", "dataTypeName", "description")])
            stamp = meta.get("rowsUpdatedAt")
            status["steps"]["metadata"] = {
                "id": dataset, "name": meta.get("name"), "rowsUpdatedAt": stamp,
                "rowsUpdatedAt_iso_utc": datetime.fromtimestamp(stamp, timezone.utc).isoformat() if isinstance(stamp, (int, float)) else None,
                "columns": [c.get("fieldName") for c in meta.get("columns", [])],
                "raw_path": str(path.relative_to(ROOT)),
            }
            save_status(status)
        return meta
    except Exception as exc:
        problem(status, f"metadata:{dataset}", exc, path)
        return None


def count_query(session, status, dataset, date_column, folder):
    url = f"{BASE}/resource/{dataset}.json"
    where = f"{date_column} >= '{START}' AND {date_column} < '{END}'"
    path = folder / "total.json"
    try:
        rows = json.loads(get_raw(session, url, path, {"$select": "count(*) as count", "$where": where}))
        count = int(rows[0]["count"])
        return count
    except Exception as exc:
        problem(status, f"count:{dataset}", exc, path)
        return None


def main_counts(session, status):
    folder = RAW / "counts"
    expected = count_query(session, status, DATASET, "created_date", folder)
    where = f"created_date >= '{START}' AND created_date < '{END}'"
    groups = {}
    for col in ("agency", "status"):
        path = folder / f"by_{col}.json"
        try:
            rows = json.loads(get_raw(session, f"{BASE}/resource/{DATASET}.json", path, {
                "$select": f"{col}, count(*) as count", "$where": where,
                "$group": col, "$order": col, "$limit": 50000,
            }))
            groups[col] = rows
            if expected is not None and sum(int(r["count"]) for r in rows) != expected:
                problem(status, f"count:by_{col}", f"group sum {sum(int(r['count']) for r in rows)} differs from total {expected}", path)
        except Exception as exc:
            problem(status, f"count:by_{col}", exc, path)
    status["steps"]["counts"] = {"total": expected, "groups": groups, "where": where}
    save_status(status)


def pull_pages(session, status, dataset, date_column, fields, folder, expected, order,
               where_override=None, select_override=None):
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "_manifest.json"
    if manifest_path.exists():
        logging.info("Existing manifest retained unchanged: %s", manifest_path)
        return json.loads(manifest_path.read_text())
    if not order:
        problem(status, f"pull:{dataset}", "No stable order field found", folder)
        return None
    start = utc_now()
    where = f"{date_column} >= '{START}' AND {date_column} < '{END}'" if where_override is None else where_override
    url = f"{BASE}/resource/{dataset}.json"
    query = {"$select": ",".join(fields) if select_override is None else select_override}
    if where:
        query["$where"] = where
    query.update({"$limit": LIMIT, "$offset": "{offset}", "$order": order})
    page_counts = []
    seen = set()
    duplicate_keys = 0
    page_number = 1
    while True:
        path = folder / f"page_{page_number:05d}.json.gz"
        params = dict(query)
        params["$offset"] = (page_number - 1) * LIMIT
        try:
            rows = json.loads(get_raw(session, url, path, params, gzip_page=True))
            if not isinstance(rows, list):
                raise ValueError("response is not a JSON array")
            page_counts.append(len(rows))
            if "unique_key" in fields:
                for row in rows:
                    key = row.get("unique_key")
                    if key in seen:
                        duplicate_keys += 1
                    else:
                        seen.add(key)
            logging.info("Page %s rows=%d cumulative=%d", path, len(rows), sum(page_counts))
            if len(rows) < LIMIT:
                break
            page_number += 1
        except Exception as exc:
            problem(status, f"pull:{dataset}", exc, path)
            return None
    actual = sum(page_counts)
    manifest = {
        "dataset_id": dataset,
        "query_url_template": requests.Request("GET", url, params=query).prepare().url,
        "pull_start_utc": start, "pull_end_utc": utc_now(),
        "page_count": len(page_counts), "rows_per_page": page_counts,
        "total_rows": actual, "expected_count": expected,
        "counts_match": actual == expected if expected is not None else None,
        "difference_actual_minus_expected": actual - expected if expected is not None else None,
        "duplicate_unique_key_count": duplicate_keys if "unique_key" in fields else None,
    }
    with manifest_path.open("x", encoding="utf-8") as out:
        json.dump(manifest, out, indent=2)
        out.write("\n")
    if expected is not None and actual != expected:
        problem(status, f"pull:{dataset}", f"count mismatch: expected={expected}, actual={actual}, difference={actual - expected}", manifest_path)
    return manifest


def main_pull(session, status):
    meta = metadata(session, status)
    if meta is None:
        return
    available = {c.get("fieldName") for c in meta.get("columns", [])}
    missing = [f for f in FIELDS if f not in available]
    for field in missing:
        problem(status, "main_columns", f"requested column missing: {field}", RAW / "metadata" / f"{DATASET}_views.json")
    selected = [f for f in FIELDS if f in available]
    if "created_date" not in selected or "unique_key" not in selected:
        problem(status, "main_pull", "created_date or unique_key missing; cannot filter/order as specified")
        return
    expected = load_status()["steps"].get("counts", {}).get("total")
    if expected is None:
        problem(status, "main_pull", "Step 2 total count unavailable; pull skipped")
        return
    manifest = pull_pages(session, status, DATASET, "created_date", selected,
                          RAW / "service_requests" / "created_2026Q2", expected, "unique_key")
    status["steps"]["main_pull"] = manifest
    save_status(status)


def catalog(session, status):
    path = RAW / "catalog" / "311_limit100.json"
    try:
        response = json.loads(get_raw(session, CATALOG, path, {"domains": "data.cityofnewyork.us", "q": "311", "limit": 100}))
        status["steps"]["catalog"] = {"path": str(path.relative_to(ROOT)), "result_count": len(response.get("results", []))}
        save_status(status)
        return response
    except Exception as exc:
        problem(status, "catalog", exc, path)
        return None


def related(session, status, dataset, date_column):
    meta = metadata(session, status, dataset)
    if meta is None:
        return
    available = [c.get("fieldName") for c in meta.get("columns", []) if c.get("fieldName")]
    if date_column not in available:
        problem(status, f"related:{dataset}", f"date column {date_column} missing", RAW / "related" / dataset / "metadata_views.json")
        return
    # Preserve all public fields. A stable unique field is needed for offset paging.
    order = next((x for x in ("unique_key", "unique_id", "id", "survey_id") if x in available), None)
    if order is None:
        problem(status, f"related:{dataset}", "no documented stable order column; metadata only", RAW / "related" / dataset / "metadata_views.json")
        return
    folder = RAW / "related" / dataset
    expected = count_query(session, status, dataset, date_column, folder)
    if expected is None:
        return
    if expected >= 2_000_000:
        status["steps"][f"related:{dataset}"] = {"expected_count": expected, "pull": "skipped: window has at least 2 million rows"}
    else:
        manifest = pull_pages(session, status, dataset, date_column, available, folder / "created_2026Q2", expected, order)
        status["steps"][f"related:{dataset}"] = {"expected_count": expected, "manifest": manifest}
    save_status(status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("metadata", "counts", "main", "catalog", "related_metadata", "related", "all_main"))
    parser.add_argument("--dataset", help="Catalog-verified related dataset ID")
    parser.add_argument("--date-column", help="Catalog-verified date field for related dataset")
    args = parser.parse_args()
    setup_log()
    status = load_status()
    session = requests.Session()
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        session.headers["X-App-Token"] = token
        logging.info("SOCRATA_APP_TOKEN is set")
    else:
        logging.info("SOCRATA_APP_TOKEN is absent")
    if args.stage in ("metadata", "all_main"):
        metadata(session, status)
    if args.stage in ("counts", "all_main"):
        main_counts(session, status)
    if args.stage in ("main", "all_main"):
        main_pull(session, status)
    if args.stage == "catalog":
        catalog(session, status)
    if args.stage == "related_metadata":
        if not args.dataset:
            parser.error("related_metadata requires --dataset")
        metadata(session, status, args.dataset)
    if args.stage == "related":
        if not args.dataset or not args.date_column:
            parser.error("related requires --dataset and --date-column")
        related(session, status, args.dataset, args.date_column)
    logging.info("Run completed")


if __name__ == "__main__":
    main()
