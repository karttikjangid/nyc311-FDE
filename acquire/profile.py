#!/usr/bin/env python3
"""Describe raw Q2 pages without changing or cleaning them."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path

import pandas as pd
from acquire import FIELDS

ROOT = Path(__file__).resolve().parents[1]
PAGE_DIR = ROOT / "data/raw/service_requests/created_2026Q2"
DATES = ["created_date", "closed_date", "due_date", "resolution_action_updated_date"]
TOP = ["agency", "status", "open_data_channel_type", "borough", "complaint_type"]


def rel(path):
    return str(path.relative_to(ROOT))


def cell(value):
    if value is None or pd.isna(value):
        return "(null)"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    out.extend("| " + " | ".join(cell(x) for x in row) + " |" for row in rows)
    return "\n".join(out)


def parse_dates(frame, col):
    if col not in frame:
        return pd.Series(pd.NaT, index=frame.index, dtype="datetime64[ns, UTC]")
    return pd.to_datetime(frame[col], errors="coerce", utc=True, format="mixed")


def main():
    status_path = ROOT / "reports/acquisition_status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {"steps": {}, "problems": []}
    manifest_path = PAGE_DIR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    pages = sorted(PAGE_DIR.glob("page_*.json.gz")) if PAGE_DIR.exists() else []
    problems = list(status.get("problems", []))
    if manifest is None:
        problems.append({"step": "profile", "message": "main pull manifest missing", "path": rel(manifest_path)})
    if not pages:
        problems.append({"step": "profile", "message": "no main pull pages", "path": rel(PAGE_DIR)})
    pull_end = pd.Timestamp(manifest["pull_end_utc"]) if manifest else pd.Timestamp(datetime.now(timezone.utc))
    rows_total = 0
    available = set(status.get("steps", {}).get("metadata", {}).get("columns", []))
    columns = [name for name in FIELDS if name in available]
    previously_loaded = 0
    nulls = Counter()
    values = {col: Counter() for col in TOP + ["resolution_description"]}
    date_info = {col: {"min": None, "max": None, "midnight": 0, "before_2010": 0, "after_pull": 0, "non_null": 0, "unparseable": 0} for col in DATES}
    anomalies = Counter()
    due_by_agency = defaultdict(lambda: [0, 0])
    close_hours = defaultdict(list)
    for path in pages:
        try:
            with gzip.open(path, "rb") as source:
                records = json.load(source)
            frame = pd.DataFrame.from_records(records).astype("string")
            for name in frame.columns:
                if name not in columns:
                    columns.append(name)
                    nulls[name] += previously_loaded
            rows_total += len(frame)
            for name in columns:
                nulls[name] += int(frame[name].isna().sum()) if name in frame else len(frame)
            previously_loaded = rows_total
            for col in values:
                if col in frame:
                    values[col].update(frame[col].value_counts(dropna=False).to_dict())
            parsed = {}
            for col in DATES:
                series = frame[col] if col in frame else pd.Series(pd.NA, index=frame.index, dtype="string")
                dates = parse_dates(frame, col)
                parsed[col] = dates
                info = date_info[col]
                info["non_null"] += int(series.notna().sum())
                info["unparseable"] += int((series.notna() & dates.isna()).sum())
                valid = dates.dropna()
                if not valid.empty:
                    minimum, maximum = valid.min(), valid.max()
                    info["min"] = minimum if info["min"] is None else min(info["min"], minimum)
                    info["max"] = maximum if info["max"] is None else max(info["max"], maximum)
                    info["midnight"] += int(((valid.dt.hour == 0) & (valid.dt.minute == 0) & (valid.dt.second == 0) & (valid.dt.microsecond == 0)).sum())
                    info["before_2010"] += int((valid < pd.Timestamp("2010-01-01", tz="UTC")).sum())
                    info["after_pull"] += int((valid > pull_end).sum())
            created, closed, due, updated = (parsed[x] for x in DATES)
            anomalies["closed_date < created_date"] += int((closed < created).sum())
            anomalies["closed_date null but status == Closed"] += int((frame.get("closed_date", pd.Series(pd.NA, index=frame.index)).isna() & frame.get("status", pd.Series(pd.NA, index=frame.index)).eq("Closed")).sum())
            anomalies["closed_date not null but status != Closed"] += int((frame.get("closed_date", pd.Series(pd.NA, index=frame.index)).notna() & frame.get("status", pd.Series(pd.NA, index=frame.index)).ne("Closed")).sum())
            anomalies["due_date < created_date"] += int((due < created).sum())
            anomalies["resolution_action_updated_date < created_date"] += int((updated < created).sum())
            if "agency" in frame:
                for agency, group in frame.groupby("agency", dropna=False):
                    key = "(null)" if pd.isna(agency) else str(agency)
                    due_by_agency[key][0] += len(group)
                    due_by_agency[key][1] += int(group["due_date"].isna().sum()) if "due_date" in group else len(group)
                valid_closed = created.notna() & closed.notna() & (closed >= created)
                subset = frame.loc[valid_closed, ["agency"]].copy()
                subset["hours"] = (closed.loc[valid_closed] - created.loc[valid_closed]).dt.total_seconds() / 3600
                for agency, group in subset.groupby("agency", dropna=False):
                    key = "(null)" if pd.isna(agency) else str(agency)
                    close_hours[key].extend(group["hours"].tolist())
        except Exception as exc:
            problems.append({"step": "profile", "message": f"could not profile page: {exc}", "path": rel(path)})
            continue
    lines = ["# NYC 311 Q2 2026 raw profile", "", "Raw descriptive inspection only. Dates without an offset were interpreted as UTC for comparisons; source strings remain unchanged.", ""]
    meta = status.get("steps", {}).get("metadata", {})
    lines += ["## Acquisition", "", f"- Main dataset: `{meta.get('id', 'unknown')}` — {meta.get('name', 'unknown')}",
              f"- `rowsUpdatedAt`: `{meta.get('rowsUpdatedAt')}`; ISO UTC: `{meta.get('rowsUpdatedAt_iso_utc')}`",
              f"- Query window: `created_date >= 2026-04-01T00:00:00 AND created_date < 2026-07-01T00:00:00`",
              f"- Raw metadata: `{meta.get('raw_path', 'missing')}`", ""]
    counts = status.get("steps", {}).get("counts", {})
    lines += ["## Pre-pull counts", "", f"- Total: **{counts.get('total', 'not available')}**", ""]
    for col in ("agency", "status"):
        rows = counts.get("groups", {}).get(col, [])
        lines += [f"### By {col}", "", table([col, "count"], [(r.get(col), r.get("count")) for r in rows]), ""]
    lines += ["## Main pull", ""]
    if manifest:
        lines += [f"- Start UTC: `{manifest['pull_start_utc']}`; end UTC: `{manifest['pull_end_utc']}`",
                  f"- Page count: **{manifest['page_count']}**; rows per page: `{manifest['rows_per_page']}`",
                  f"- Total rows: **{manifest['total_rows']}**; expected: **{manifest['expected_count']}**; match: **{manifest['counts_match']}**; difference: **{manifest['difference_actual_minus_expected']}**",
                  f"- Duplicate `unique_key` occurrences across pages: **{manifest['duplicate_unique_key_count']}**",
                  f"- Query URL template: `{manifest['query_url_template']}`", ""]
    lines += ["## Raw profile", "", f"- Rows successfully loaded into pandas as strings: **{rows_total}**",
              f"- Columns: {', '.join('`' + col + '`' for col in columns) if columns else '(none)'}", "",
              "### Nulls", "", table(["column", "null count", "null %"], [(c, nulls[c], f"{100 * nulls[c] / rows_total:.2f}%" if rows_total else "n/a") for c in columns]), ""]
    for col in TOP:
        lines += [f"### Top 30: {col}", "", table([col, "count"], [(k, n) for k, n in values[col].most_common(30)]), ""]
    lines += ["### Top 50: resolution_description", "", "Counts are for full, unmodified strings; display text is truncated to 150 characters.", "",
              table(["resolution_description (first 150 chars)", "count"], [(str(k)[:150] if not pd.isna(k) else None, n) for k, n in values["resolution_description"].most_common(50)]), ""]
    lines += ["### Date fields", "", table(["field", "min UTC", "max UTC", "exact midnight", "before 2010", "after pull end", "non-null", "unparseable"],
              [(col, info["min"].isoformat() if info["min"] is not None else None, info["max"].isoformat() if info["max"] is not None else None,
                info["midnight"], info["before_2010"], info["after_pull"], info["non_null"], info["unparseable"]) for col, info in date_info.items()]), ""]
    lines += ["### Date/status inconsistencies", "", table(["condition", "count"], sorted(anomalies.items())), ""]
    lines += ["### due_date null by agency", "", table(["agency", "rows", "due_date null", "due_date null %"],
              [(a, n, missing, f"{100 * missing / n:.2f}%") for a, (n, missing) in sorted(due_by_agency.items())]), ""]
    lines += ["### RAW, NOT A METRIC: closed_date minus created_date by agency", "",
              "Hours on rows where both timestamps parse and `closed_date >= created_date`. No status or quality interpretation is implied.", "",
              table(["agency", "eligible rows", "median hours", "90th percentile hours"],
                    [(a, len(hours), f"{pd.Series(hours).median():.3f}", f"{pd.Series(hours).quantile(0.9):.3f}") for a, hours in sorted(close_hours.items())]), ""]
    selection_path = ROOT / "reports/related_selection.json"
    selection = json.loads(selection_path.read_text()) if selection_path.exists() else []
    lines += ["## Related 311 datasets", "", "Catalog response: `data/raw/catalog/311_limit100.json`", ""]
    if selection:
        lines += [table(["role", "id", "name", "description", "update frequency", "row count shown", "one row represents", "Q2 pull"],
                        [(x.get("role"), x.get("id"), x.get("name"), x.get("description"), x.get("update_frequency"), x.get("row_count_shown"), x.get("one_row"), x.get("q2_pull")) for x in selection]), ""]
        for x in selection:
            dataset = x["id"]
            related_dir = ROOT / "data/raw/related" / dataset
            related_manifest = related_dir / "created_2026Q2/_manifest.json"
            lines.append(f"- `{dataset}` metadata: `{rel(related_dir / 'metadata_views.json')}`" +
                         (f"; Q2 count: `{rel(related_dir / 'total.json')}`; manifest: `{rel(related_manifest)}`" if related_manifest.exists() else ""))
            if related_manifest.exists():
                item = json.loads(related_manifest.read_text())
                if item.get("counts_match") is False:
                    problems.append({"step": f"related:{dataset}", "message": f"count mismatch: expected={item.get('expected_count')}, actual={item.get('total_rows')}", "path": rel(related_manifest)})
        lines.append("")
    else:
        lines += ["No related dataset selection has been recorded.", ""]
    lines += ["## Problems", ""]
    if rows_total != (manifest or {}).get("total_rows", 0):
        problems.append({"step": "profile", "message": f"loaded rows {rows_total} differ from manifest total {(manifest or {}).get('total_rows')}", "path": rel(PAGE_DIR)})
    for col, info in date_info.items():
        if info["unparseable"]:
            problems.append({"step": "profile", "message": f"{col}: {info['unparseable']} non-null date strings could not be parsed", "path": rel(PAGE_DIR)})
        if info["before_2010"] or info["after_pull"]:
            problems.append({"step": "profile", "message": f"{col}: {info['before_2010']} values before 2010; {info['after_pull']} after pull end", "path": rel(PAGE_DIR)})
    for label, count in anomalies.items():
        if count:
            problems.append({"step": "profile", "message": f"{label}: {count}", "path": rel(PAGE_DIR)})
    if manifest and manifest.get("duplicate_unique_key_count"):
        problems.append({"step": "main_pull", "message": f"duplicate unique_key occurrences: {manifest['duplicate_unique_key_count']}", "path": rel(manifest_path)})
    for log_path in sorted((ROOT / "logs").glob("acquire_*.log")):
        retry_lines = [line.strip() for line in log_path.read_text().splitlines() if " RETRY " in line]
        if retry_lines:
            problems.append({"step": "acquisition_retries", "message": f"{len(retry_lines)} retry event(s); see log for status, delay, and request details", "path": rel(log_path)})
    if problems:
        for p in problems:
            lines.append(f"- **{p.get('step')}**: {p.get('message')} — `{p.get('path') or 'n/a'}`")
    else:
        lines.append("- None observed.")
    lines += ["", "## Deliverables checklist", ""]
    checks = [
        ("nyc311/acquire/*.py (rerunnable)", bool(list((ROOT / "acquire").glob("*.py")))),
        ("nyc311/data/raw/metadata/*", (ROOT / "data/raw/metadata/erm2-nwe9_views.json").exists() and (ROOT / "data/raw/metadata/erm2-nwe9_columns.csv").exists()),
        ("nyc311/data/raw/counts/*", all((ROOT / "data/raw/counts" / f).exists() for f in ("total.json", "by_agency.json", "by_status.json"))),
        ("nyc311/data/raw/service_requests/created_2026Q2/page_*.json.gz + _manifest.json", bool(pages) and bool(manifest)),
        ("nyc311/data/raw/<other datasets>/* (if found)", bool(selection) and all((ROOT / "data/raw/related" / x["id"] / "metadata_views.json").exists() for x in selection if x.get("id"))),
        ("nyc311/reports/raw_profile.md", True),
        ("nyc311/logs/acquire_<UTC timestamp>.log", bool(list((ROOT / "logs").glob("acquire_*.log")))),
    ]
    lines += [f"- {'done' if done else 'not done'} — {label}" for label, done in checks]
    path = ROOT / "reports/raw_profile.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    pull2 = "\n## Pull 2\n" + existing.split("\n## Pull 2\n", 1)[1] if "\n## Pull 2\n" in existing else ""
    path.write_text("\n".join(lines) + "\n" + pull2, encoding="utf-8")
    print(f"Wrote {path}; profiled rows={rows_total}; problems={len(problems)}")
    print("Deliverables checklist:")
    for label, done in checks:
        print(f"{'done' if done else 'not done'} — {label}")


if __name__ == "__main__":
    main()
