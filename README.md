# NYC 311: can the City's own data tell a resident where their request is?

FDE Data Foundations assignment (Classes 4 to 8), Track C. Kartik Jangid.

## The problem

**Client:** City of New York, 311 and the Office of Technology and Innovation (OTI).

**The ask:** "Build an AI assistant that tells residents where their 311 request is and when it will be fixed."

**What we did first:** checked whether the City's published 311 records can answer that question truthfully, request by request, before anyone builds an assistant on top of them. "Service Request Status" was the second most common topic in agent-handled 311 calls last quarter (20,389 calls, April to June 2026), so the demand is real. The question is whether the data behind the answer holds up.

**Decision this output supports:** for each complaint type, should 311/OTI and the agency start a measurement pilot, fix a named data problem first, or hold? The evidence table gives that call per type, with the owner of each fix.

## Stakeholders

| Who | What they own | What they need from this |
|---|---|---|
| 311 / OTI leadership | the 311 platform and the open data feed; the build decision | which complaint types are safe to pilot, and what to fix |
| Agencies (HPD, NYPD, DOT, DOB) | closing notes, closure rules, response targets | where their records fail, and the exact rows |
| 311 call center | status calls | whether answers could come from the record |
| Residents | the question | an answer that does not claim a fix that did not happen |

Nobody formally owns the definition of "answered". We propose one below and name who should confirm it.

## KPI and metrics

**Project KPI: record-answerability.** Share of requests whose record passes all five checks at the as-of time:

| Check | Question |
|---|---|
| A1 | Are the dates in a possible order? |
| A2 | Do status and closed date agree? |
| A3 | Does the closing note say what happened (closed) or who acts next (open)? |
| A4 | Does an open request have a published response target? |
| A5 | Is the status held in 311, not only in another agency system? |

Supporting metrics: agency action mix (intervention), next step stated for open requests, weekly status-call volume (context). Guardrail: Closed requests whose note gives no evidence of a fix.

"Answerable" means the record can tell the resident, in plain words, what happened. It does not mean the problem was fixed. Details: [`docs/03_data_model.md`](docs/03_data_model.md).

## Results (as-of 2026-09-25)

| | NYPD | HPD | DOT | DOB |
|---|---:|---:|---:|---:|
| Requests (Apr to Jun 2026) | 460,240 | 159,275 | 76,000 | 30,604 |
| Record-answerability | 98.0% | 96.0% | 60.3% | 66.9% |
| Same, strict reading of the notes | 71.5% | 68.9% | 39.8% | 63.3% |
| Closed without fix evidence (guardrail) | 73.8% | 90.8% | 77.2% | 100.0% |

- Most Closed requests carry no evidence that anything was fixed. An assistant that reads `status` would mislead residents.
- Whether a complaint type is ready depends on how a handful of hedged closing notes are read. Loose reading: 31 of 49 large complaint types qualify for a pilot. Strict reading: 4. The agencies, not us, have to settle what those notes mean.
- One NYPD template ("no criminal violation existed ... the condition was corrected") covers 120,685 requests and moves NYPD's score by 26.5 points.
- For a third of DOT requests (33.1%), the note points elsewhere for the status, mostly to DOT's website (20,225 requests): 311 does not hold it.
- `due_date` is empty for 99.6% of requests, so "when will it be fixed" has no answer in the data.

Proposed decision (strict reading): 4 complaint types (12,681 requests) are candidates for a measurement pilot, 28 need a named fix first, 17 should hold; 7 of those hold under either reading. Full evidence, decision table and Known / Unknown / Assumption / Limitation: [`docs/04_evidence.md`](docs/04_evidence.md).

## Sources

| Source | Id | Retrieval | Use |
|---|---|---|---|
| 311 Service Requests from 2020 to Present | `erm2-nwe9` | JSON API, keyset pagination, SoQL count | core facts |
| 311 Call Center Inquiry | `wewp-mm3p` | JSON API, SoQL count | status-call context |
| 311 Service Level Agreements | `cs9t-e3x8` | JSON file snapshot | response targets (2024) |
| 311 Resolution Satisfaction Survey | `5ijn-vbdv` | JSON file snapshot | resident-view context |

Plus SQL: the model is built and queried in SQLite (`sql/`). Owners, grain, freshness and source-of-truth decisions: [`docs/01_source_map.md`](docs/01_source_map.md).

## Run it

Python 3.10+.

```bash
python3 -m venv .venv && source .venv/bin/activate   # macOS/Homebrew Python blocks system-wide pip installs
python3 -m pip install -r requirements.txt

# Replay the saved snapshot, offline (reproduces the published results in output/run_date=2026-09-25)
python3 run_pipeline.py --run-date 2026-09-25 --snapshot-id 20260925T112431Z_initial

# Pull a fresh snapshot from NYC Open Data first (about 10 to 15 minutes), then run on it
python3 run_pipeline.py --run-date 2026-09-26 --source live

# Controlled failures (scratch run date, so the published 2026-09-25 results stay untouched)
python3 run_pipeline.py --run-date 2026-09-27 --snapshot-id 20260925T112431Z_initial --chaos missing_column         # blocked, nothing published
python3 run_pipeline.py --run-date 2026-09-27 --snapshot-id 20260925T112431Z_initial --chaos stale_data             # blocked, nothing published
python3 run_pipeline.py --run-date 2026-09-27 --snapshot-id 20260925T112431Z_initial --chaos conflicting_duplicate  # blocked
python3 run_pipeline.py --run-date 2026-09-27 --snapshot-id 20260925T112431Z_initial --chaos duplicate_order        # published with a warning
python3 run_pipeline.py --run-date 2026-09-27 --snapshot-id 20260925T112431Z_initial --chaos unmapped_notes         # blocked: note coverage too low

# Tests
python3 -m pytest -q
```

Without `--snapshot-id`, a replay uses the newest complete snapshot. The run date is a logical date: replaying with the same date and snapshot always gives the same files. Optional: set `SOCRATA_APP_TOKEN` for higher API limits. Add `--keep-model` to keep the SQLite model (about 600 MB).

**What happens:** EXTRACT (raw pages + SHA-256 manifest) -> VALIDATE (26 rules, two severities) -> CLEAN (types and flags, no silent fixes) -> MODEL (SQLite) -> METRICS (SQL) -> SAVE (temp folder, then an atomic swap) -> LOG. A blocking failure publishes nothing and keeps the previous output. Running the same date twice gives identical files.

**Outputs** in `output/run_date=YYYY-MM-DD/`: `evidence_table.md`, `gate2.md`, `validation_report.json`, `metrics.json`, one CSV per metric, `request_journey_sample.csv`. Logs in `logs/`.

## Where each part of the brief lives

| Brief (class) | Evidence in this repo |
|---|---|
| Understand sources (4) | [`docs/01_source_map.md`](docs/01_source_map.md): information need to field to source to owner; source contracts; source-of-truth decisions; gaps |
| Retrieve data (5) | `pipeline/extract.py` (API keyset paging, SoQL counts, retries, raw pages + SHA-256), `data/raw/snapshots/*/manifest.json`, `tests/test_extract.py`, `tests/test_http.py` |
| Profile and validate (6) | `reports/raw_profile.md`, [`docs/02_validation_contract.md`](docs/02_validation_contract.md), `pipeline/validate.py`, `output/run_date=*/validation_report.json` |
| Model workflow (7) | [`docs/03_data_model.md`](docs/03_data_model.md), `sql/model.sql`, `reference/` (closing-note coding), `output/run_date=*/request_journey_sample.csv` |
| Dependable pipeline (8) | `run_pipeline.py`, `config/pipeline.json`, `tests/test_pipeline.py`, [`docs/05_gate2_readiness.md`](docs/05_gate2_readiness.md) |
| Evidence table, Known / Unknown / Assumption / Limitation | [`docs/04_evidence.md`](docs/04_evidence.md), `output/run_date=2026-09-25/evidence_table.md`, `notebooks/evidence_walkthrough.ipynb` |

## Repository

```
config/pipeline.json        all settings and thresholds
pipeline/                   extract, validate, clean, sla, mapping, model, metrics, save, chaos
sql/model.sql               workflow views and the five checks
sql/metrics/*.sql           one file per metric
reference/                  codebook, coded notes (v1, second coder, adjudicated v2), adjudication log
data/raw/                   raw API pages (gzip) and snapshot manifests
output/                     published results by run date
tests/                      unit and end-to-end tests
notebooks/                  evidence walkthrough (reads the published outputs, with charts)
docs/                       source map, validation contract, data model, evidence, Gate 2
acquire/, reports/          first acquisition script and raw profile (superseded by pipeline/extract.py)
```

## Judgement calls

- **We did not build the assistant.** The data cannot define "fixed", so no model could learn to say it.
- **Closed is not fixed.** Outcomes come from the closing note, coded into action, finding, fix evidence and next step, with a strict reading reported beside the loose one.
- **A second, blind coder checked the note coding.** Agreement was 77% to 95% per field; 19 codes changed after adjudication, and that moved HPD's strict score from 90.4% to 68.9% ([`reference/adjudication_v1_to_v2.md`](reference/adjudication_v1_to_v2.md)).
- **A 00:00 timestamp on the creation day is date-only precision, not an error.** Counting it as an error would have failed 8,514 good HPD and DOB records.
- **The SLA table is a response target from 2024, not a repair date.** It is used as a match state, never as a promise.
- **Survey and call data stay context.** Neither has a request key.

## Data

NYC Open Data, published by the City of New York under its open data terms of use. The raw pages in `data/raw/` are unchanged API responses.
