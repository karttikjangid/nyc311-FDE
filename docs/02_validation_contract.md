# Validation contract

Code: `pipeline/validate.py`. Results for each run: `output/run_date=*/validation_report.json` and `gate2.md`.

Each rule turns a business assumption into a check with two severities, because the same data can be fine for a weekly report and unsafe for a live answer to one resident (Class 6).

- **Reporting**: safe for the weekly evidence report?
- **Live**: safe for telling one resident about one request right now?
- **Blocking**: a reporting FAIL stops the run. Nothing is published and the previous output stays.

Statuses: PASS / WARN / FAIL / UNKNOWN. UNKNOWN means we cannot measure it, never PASS.

| Rule | Business assumption | Check | Reporting severity | Live severity | Blocking | Action when it fails |
|---|---|---|---|---|---|---|
| R01 | We received every row that exists | received rows = SoQL `count(*)` before the pull; count after the pull compared too | FAIL on mismatch; WARN if the source count moved during the pull | same | yes | Stop. Re-pull. |
| R02 | Replayed files are the bytes the API returned | SHA-256 of every raw page vs the manifest | FAIL on any mismatch | same | yes | Stop. Restore or re-pull. |
| R03 | Needed columns exist | required columns per source (config) | FAIL if any missing | same | yes | Stop. Schema change: talk to OTI. |
| R04 | Full SLA key available | `descriptor_2` present | WARN if missing | WARN | no | SLA matched at detail level only |
| R05 | One row per request | exact duplicates removed and counted; same key with different values | WARN for exact duplicates; FAIL for conflicting ones | same | yes | Conflicts need an owner to pick a version |
| R06 | Dates are valid | unparseable timestamps | FAIL above 1%, WARN above 0 | same | yes | Stop above threshold |
| R07 | We got the cohort we asked for | `created_date` inside the configured window | FAIL on any row outside | same | yes | Stop. Query bug. |
| R08 | Data is recent for the run | run date minus snapshot date | FAIL above 7 days | UNKNOWN (publication lag vs agency systems cannot be measured) | yes | Pull a new snapshot |
| R09 | Events happen in a possible order | closed or last-action time before creation, **excluding** 00:00 stamps on the creation date (date-only precision, see R11) | WARN up to 2% of rows, FAIL above | FAIL for affected rows | no | Row fails check A1 |
| R10 | Status and closed date agree | Closed without closed date, or closed date on a non-Closed status | WARN up to 2%, FAIL above | FAIL for affected rows | no | Row fails check A2 |
| R11 | Closure times have hour precision | share of closures at exactly 00:00 per agency; date-only stamps earlier than creation | WARN if an agency is above 50% or such stamps exist | WARN | no | Exclude from hour-level durations; ask the agency |
| R12 | Nothing happens after the pull | any timestamp after the as-of time | WARN | FAIL | no | Investigate clock or timezone |
| R13 | Status values are known | values outside the documented set | WARN | FAIL | no | Owner must define the new value |
| R14 | Every request has a closing note | note missing, empty or "N/A" | WARN up to 5%, FAIL above | FAIL for affected rows | no | Row fails check A3 |
| R15 | Note text is intact | broken encoding ("Ã", "â€"); notes cut at exactly 500 characters mid-sentence (heuristic) | WARN | FAIL | no | Report to agency and OTI |
| R16 | The note mapping is valid | every code is an allowed value; no duplicate hashes | FAIL | FAIL | yes | Fix the mapping file |
| R17 | The mapping covers the focus-agency notes | share of focus-agency requests with a coded note | PASS at 95%+, WARN 90 to 95%, FAIL below 90% | same | yes | Code the new wording (new notes count as UNKNOWN, never dropped) |
| R18 | Another reader codes the notes the same way | Cohen's kappa per field vs the blind second coder | PASS if the lowest kappa is 0.60+, WARN below, UNKNOWN if no second coder | UNKNOWN (needs agency sign-off) | no | Resolve disagreements in writing |
| R19 | SLA units are understood | every `sla_days` is "N hours", "N days" or the sentinel | WARN on anything else | WARN | no | Days are treated as calendar days (UNVERIFIED) |
| R20 | The SLA table still applies | days between SLA update and snapshot | WARN above 365 days | FAIL | no | Ask 311 for current, dated targets |
| R21 | Each request has one target | share of requests with AMBIGUOUS match | WARN if any | WARN | no | Needs the full hierarchy or an owner rule |
| R22 | Joins do not duplicate rows | row count before and after SLA and mapping joins | FAIL on any change | FAIL | yes | Fix the join key |
| R23 | Timestamps are New York time | publisher does not say | UNKNOWN | UNKNOWN | no | Assumption stored in config; ask OTI |
| R24 | Status calls can be tied to an agency | `agency` empty in call rows | WARN | WARN | no | Calls stay context only |
| R25 | Survey answers describe all requests | selection: only residents who gave contact details and chose to answer | WARN | FAIL | no | Survey stays context only |
| R26 | The model reconciles | each request-grain table has exactly one row per cleaned request | FAIL on mismatch | FAIL | yes | Stop. Model bug. |

## Gates

- **Weekly evidence reporting**: READY when no blocking rule fails. Warnings are published with the report.
- **Live answers to residents**: READY only when no rule is FAIL or UNKNOWN at live severity. With today's sources this cannot happen (R08, R20, R23 and R25 are structural), which is itself a finding.

## Thresholds

Numbers live in `config/pipeline.json` (`thresholds`), not in code. They are our proposals. The owner who should confirm them is 311/OTI leadership.
