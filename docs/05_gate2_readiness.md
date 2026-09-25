# Gate 2: data readiness review

Template from the instructor's Class 8 project, filled in with evidence from this repository.
The pipeline also writes a generated version for every run: `output/run_date=*/gate2.md`.

## Pipeline run

- [x] Complete flow runs with one command: `python3 run_pipeline.py --run-date 2026-09-25`
- [x] Same run can be safely repeated: two runs of 2026-09-25 produced byte-identical output folders (`diff -r` empty); covered by `tests/test_pipeline.py::test_run_publishes_and_rerun_is_identical`
- [x] Raw API responses are preserved: gzip pages under `data/raw/`, SHA-256 of each page in the snapshot `manifest.json`, re-checked on every replay (R02)
- [x] Processed output is written only after validation: results go to `output/.tmp_run_date=*` and are swapped in only if no blocking rule fails

## Validation

| Check | Status | Evidence / note |
|---|---|---|
| Required columns | PASS | R03; chaos `missing_column` blocks the run and keeps the old output |
| Critical nulls | WARN | R14: 26,087 requests (2.7%) have no usable closing note; R10: 4,225 status/date conflicts |
| Order uniqueness | PASS | R05: 0 duplicate `unique_key`; chaos `duplicate_order` warns and removes exact duplicates, `conflicting_duplicate` blocks |
| Freshness | PASS for reporting, UNKNOWN for live | R08: snapshot age 0 days; chaos `stale_data` blocks. Lag behind agency systems cannot be measured |
| Retrieval completeness | PASS | R01: 969,004 service requests received = API count; call center, SLA and survey also match |

## Reliability

| Capability | Status | Evidence / note |
|---|---|---|
| Bounded retries | PASS | `pipeline/http.py`: 5 retries, exponential backoff, honours `Retry-After`, only on 429/5xx/timeouts; `tests/test_http.py` |
| Useful failure message | PASS | log line names the rule and its evidence; full detail in `logs/failed_run_*.json` |
| Logging | PASS | `logs/pipeline_<run_date>.log`, one line per stage and per rule |
| Idempotent rerun | PASS | output partition keyed by logical run date, atomic swap, deterministic files |
| Configuration outside core logic | PASS | `config/pipeline.json`: dataset ids, window, page size, retry budget, thresholds, timezone |

## Known limitations

- No status history: the source publishes one current row per request.
- No field says whether a problem was physically fixed; `due_date` is 99.6% empty.
- Closing-note coding is ours (110 notes, blind second coder as a check) and needs agency sign-off.
- SLA reference last updated 2024-03-05.
- Timezone assumed (America/New_York).
- Status calls and survey answers cannot be linked to requests.

## Gate decision

**Weekly evidence reporting: READY (with warnings).**
Reason: every blocking rule passes; warnings are published with the report.

**Live answers to residents: NOT READY.**
Reason: R09, R10, R14 and R15 fail at live severity for affected rows, and R08, R18, R20, R23 and R25 are FAIL or UNKNOWN by design of the sources. No change to this pipeline can fix those; they need changes to the 311 platform (listed in `04_evidence.md`, section 3).
