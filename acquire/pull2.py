#!/usr/bin/env python3
"""Pull two small reference datasets and append their raw profiles."""

from collections import Counter
import argparse
import gzip
import json
import logging
import os
from pathlib import Path

import pandas as pd
import requests

from acquire import (BASE, RAW, ROOT, get_raw, load_status, metadata, problem,
                     pull_pages, save_status, setup_log)


SLA = "cs9t-e3x8"
SURVEY = "5ijn-vbdv"


def relative(path):
    return str(path.relative_to(ROOT))


def metadata_fields(session, status, dataset, required):
    meta = metadata(session, status, dataset)
    if meta is None:
        return None
    fields = [col.get("fieldName") for col in meta.get("columns", []) if col.get("fieldName")]
    missing = [name for name in required if name not in fields]
    if missing:
        problem(status, f"pull2:{dataset}", f"required columns missing: {', '.join(missing)}",
                RAW / "related" / dataset / "metadata_views.json")
        return None
    return fields


def count_all(session, status):
    path = RAW / "related" / SLA / "full_count.json"
    try:
        body = get_raw(session, f"{BASE}/resource/{SLA}.json", path,
                       {"$select": "count(*)"})
        rows = json.loads(body)
        if len(rows) != 1 or len(rows[0]) != 1:
            raise ValueError(f"expected one count cell, received: {rows!r}")
        return int(next(iter(rows[0].values())))
    except Exception as exc:
        problem(status, f"pull2:count:{SLA}", exc, path)
        return None


def count_year_month(session, status):
    path = RAW / "related" / SURVEY / "by_year_month.json"
    params = {"$select": "year,month,count(*)", "$group": "year,month",
              "$order": "year,month", "$limit": 50000}
    try:
        rows = json.loads(get_raw(session, f"{BASE}/resource/{SURVEY}.json", path, params))
        if not isinstance(rows, list):
            raise ValueError("grouped count response is not an array")
        expected = 0
        for row in rows:
            if "year" not in row or "month" not in row or "count" not in row:
                raise ValueError(f"grouped count row missing year/month/count: {row!r}")
            year = row["year"]
            if year is not None and int(year) >= 2025:
                expected += int(row["count"])
        return rows, expected
    except Exception as exc:
        problem(status, f"pull2:count:{SURVEY}", exc, path)
        return None, None


def run_sla(session, status):
    fields = metadata_fields(session, status, SLA,
                             ("agency", "problem", "problem_details", "additional_details", "sla_days"))
    if fields is None:
        return
    expected = count_all(session, status)
    if expected is None:
        return
    manifest = pull_pages(session, status, SLA, None, fields,
                          RAW / "related" / SLA / "full", expected, ":id",
                          where_override="", select_override="*")
    status["steps"]["pull2_sla"] = {"expected_count": expected, "manifest": manifest}
    save_status(status)


def run_survey(session, status):
    fields = metadata_fields(session, status, SURVEY,
                             ("unique_key", "year", "month", "overall_satisfaction",
                              "dissatisfaction_reason", "complaint_type"))
    if fields is None:
        return
    grouped, expected = count_year_month(session, status)
    if grouped is None:
        return
    manifest = pull_pages(session, status, SURVEY, None, fields,
                          RAW / "related" / SURVEY / "year_gte_2025", expected,
                          "unique_key", where_override="year >= 2025",
                          select_override="*")
    status["steps"]["pull2_survey"] = {"expected_count": expected,
                                         "grouped_count_rows": len(grouped),
                                         "manifest": manifest}
    save_status(status)


def cell(value):
    if value is None or pd.isna(value):
        return "(null)"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def table(headings, rows):
    output = ["| " + " | ".join(headings) + " |",
              "| " + " | ".join(["---"] * len(headings)) + " |"]
    output += ["| " + " | ".join(cell(x) for x in row) + " |" for row in rows]
    return "\n".join(output)


def read_pages(folder, problems, profile_columns, sample_size=0):
    counts = Counter()
    values = {}
    samples = []
    total = 0
    pages = sorted(folder.glob("page_*.json.gz")) if folder.exists() else []
    for path in pages:
        try:
            with gzip.open(path, "rb") as source:
                records = json.load(source)
            if not isinstance(records, list):
                raise ValueError("page is not a JSON array")
            total += len(records)
            if len(samples) < sample_size:
                samples.extend(records[:sample_size - len(samples)])
            frame = pd.DataFrame.from_records(records).reindex(columns=profile_columns).astype("string")
            for col in frame.columns:
                values.setdefault(col, Counter()).update(frame[col].value_counts(dropna=False).to_dict())
        except Exception as exc:
            problems.append(f"{relative(path)}: could not profile raw page: {exc}")
    counts["total"] = total
    counts["page_count"] = len(pages)
    return counts, values, samples


def manifest_info(folder, counts, problems):
    path = folder / "_manifest.json"
    if not path.exists():
        problems.append(f"{relative(path)}: missing manifest")
        return None
    try:
        manifest = json.loads(path.read_text())
        if counts["total"] != manifest.get("total_rows"):
            problems.append(f"{relative(path)}: profiled {counts['total']} rows versus manifest {manifest.get('total_rows')}")
        if counts["page_count"] != manifest.get("page_count"):
            problems.append(f"{relative(path)}: found {counts['page_count']} pages versus manifest {manifest.get('page_count')}")
        if manifest.get("counts_match") is False:
            problems.append(f"{relative(path)}: expected {manifest.get('expected_count')} rows, received {manifest.get('total_rows')}")
        return manifest
    except Exception as exc:
        problems.append(f"{relative(path)}: could not read manifest: {exc}")
        return None


def count_table(values, col, limit=None):
    counter = values.get(col, Counter())
    items = counter.most_common(limit) if limit else counter.most_common()
    return table([col, "count"], items)


def append_report(log_path):
    report_path = ROOT / "reports/raw_profile.md"
    source = report_path.read_text(encoding="utf-8") if report_path.exists() else "# NYC 311 raw profile\n"
    base = source.split("\n## Pull 2\n", 1)[0].rstrip() + "\n"
    problems = []
    sla_folder = RAW / "related" / SLA / "full"
    survey_folder = RAW / "related" / SURVEY / "year_gte_2025"
    sla_counts, sla_values, sla_samples = read_pages(sla_folder, problems,
                                                    ("agency", "sla_days"), sample_size=20)
    survey_counts, survey_values, _ = read_pages(survey_folder, problems,
                                                  ("overall_satisfaction", "dissatisfaction_reason", "complaint_type"))
    sla_manifest = manifest_info(sla_folder, sla_counts, problems)
    survey_manifest = manifest_info(survey_folder, survey_counts, problems)
    grouped_path = RAW / "related" / SURVEY / "by_year_month.json"
    grouped = []
    if grouped_path.exists():
        try:
            grouped = json.loads(grouped_path.read_text())
        except Exception as exc:
            problems.append(f"{relative(grouped_path)}: could not read grouped counts: {exc}")
    else:
        problems.append(f"{relative(grouped_path)}: missing grouped count response")
    full_count_path = RAW / "related" / SLA / "full_count.json"
    if not full_count_path.exists():
        problems.append(f"{relative(full_count_path)}: missing full count response")
    for label, counts, values, fields, folder in (
        ("SLA", sla_counts, sla_values, ("agency", "sla_days"), sla_folder),
        ("survey", survey_counts, survey_values,
         ("overall_satisfaction", "dissatisfaction_reason", "complaint_type"), survey_folder),
    ):
        for field in fields:
            observed = sum(values.get(field, Counter()).values())
            if observed != counts["total"]:
                problems.append(f"{relative(folder)}: {label} {field} value counts total {observed} versus rows {counts['total']}")
    status = load_status()
    for item in status.get("problems", []):
        if str(item.get("step", "")).startswith(("pull2:", f"pull:{SLA}", f"pull:{SURVEY}")):
            problems.append(f"{item.get('path')}: {item.get('message')}")
    acquisition_logs = []
    for candidate in sorted((ROOT / "logs").glob("acquire_*.log")):
        log_text = candidate.read_text()
        if "Saved raw response:" in log_text and any(part in log_text for part in (
            f"/related/{SLA}/full_count.json", f"/related/{SLA}/full/page_",
            f"/related/{SURVEY}/by_year_month.json", f"/related/{SURVEY}/year_gte_2025/page_",
        )):
            acquisition_logs.append(candidate)
        retries = [line for line in log_text.splitlines() if " RETRY " in line and (SLA in line or SURVEY in line)]
        if retries:
            problems.append(f"{relative(candidate)}: {len(retries)} Pull 2 retry event(s), with details in the log")
    lines = ["", "## Pull 2", "", "Raw reference-dataset pulls and descriptive counts only. No values were cleaned or changed.", "",
             "### A. 311 Service Level Agreements (`cs9t-e3x8`)", "",
             f"- Count response: `{relative(full_count_path)}`",
             f"- Rows received: **{sla_counts['total']}**; expected: **{sla_manifest.get('expected_count') if sla_manifest else 'unavailable'}**; match: **{sla_manifest.get('counts_match') if sla_manifest else 'unavailable'}**",
             f"- Pages: **{sla_counts['page_count']}**; manifest: `{relative(sla_folder / '_manifest.json')}`", "",
             f"Distinct `agency` values: {', '.join('`' + cell(v) + '`' for v in sorted(sla_values.get('agency', Counter()), key=lambda x: cell(x))) if sla_values.get('agency') else '(none)'}", "",
             "#### First 20 rows in raw page order", "", "```jsonl"]
    lines.extend(json.dumps(row, ensure_ascii=False) for row in sla_samples)
    lines += ["```", "", "#### `sla_days` values", "", count_table(sla_values, "sla_days"), "",
              "### B. 311 Resolution Satisfaction Survey (`5ijn-vbdv`)", "",
              f"- Grouped count response: `{relative(grouped_path)}`",
              f"- Rows with `year >= 2025` received: **{survey_counts['total']}**; expected from grouped counts: **{survey_manifest.get('expected_count') if survey_manifest else 'unavailable'}**; match: **{survey_manifest.get('counts_match') if survey_manifest else 'unavailable'}**",
              f"- Pages: **{survey_counts['page_count']}**; manifest: `{relative(survey_folder / '_manifest.json')}`", "",
              "#### Counts by year and month (all periods in grouped response)", "",
              table(["year", "month", "count"], [(row.get("year"), row.get("month"), row.get("count")) for row in grouped]), "",
              "#### `overall_satisfaction` values", "", count_table(survey_values, "overall_satisfaction"), "",
              "#### `dissatisfaction_reason` values", "", count_table(survey_values, "dissatisfaction_reason"), "",
              "#### Top 20 `complaint_type` values", "", count_table(survey_values, "complaint_type", 20), "",
              "Acquisition log(s): " + (", ".join(f"`{relative(path)}`" for path in acquisition_logs) if acquisition_logs else "(none found)"), "",
              "### Pull 2 Problems", ""]
    lines += ["- " + issue for issue in problems] if problems else ["- None observed."]
    lines += ["", "### Pull 2 deliverables checklist", ""]
    checks = [
        ("SLA raw all-row count", full_count_path.exists()),
        ("SLA full pages and manifest", bool(sla_counts["page_count"]) and sla_manifest is not None),
        ("Survey raw year/month counts", grouped_path.exists()),
        ("Survey year >= 2025 pages and manifest", bool(survey_counts["page_count"]) and survey_manifest is not None),
        ("Pull 2 report section", True),
        ("Pull 2 UTC acquisition log", bool(acquisition_logs)),
    ]
    lines += [f"- {'done' if done else 'not done'} — {label}" for label, done in checks]
    report_path.write_text(base + "\n".join(lines) + "\n", encoding="utf-8")
    print(f"Appended Pull 2 to {report_path}; problems={len(problems)}")
    print("Deliverables checklist:")
    for label, done in checks:
        print(f"{'done' if done else 'not done'} — {label}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("all", "sla", "survey", "report"), nargs="?", default="all")
    args = parser.parse_args()
    log_path = setup_log()
    status = load_status()
    session = requests.Session()
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        session.headers["X-App-Token"] = token
        logging.info("SOCRATA_APP_TOKEN is set")
    else:
        logging.info("SOCRATA_APP_TOKEN is absent")
    if args.stage in ("all", "sla"):
        run_sla(session, status)
    if args.stage in ("all", "survey"):
        run_survey(session, status)
    append_report(log_path)
    logging.info("Pull 2 completed")


if __name__ == "__main__":
    main()
