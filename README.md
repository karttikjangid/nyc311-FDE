# NYC 311 Service Request Status: Data Readiness Assessment for an AI Assistant

FDE Data Foundations assignment (Classes 4 to 8), Track C. Kartik Jangid.

## The problem in plain words

New Yorkers report problems to the City through 311: a noisy neighbour, no heat, a pothole. Each report becomes a "service request" that a City agency handles and then closes.

The City wants an **AI assistant** that answers residents who ask: *"What happened to my request, and when will it be fixed?"* Residents do ask this a lot: it was the second most common topic in 311 phone calls between April and June 2026 (20,389 calls).

An assistant can only be as honest as the records it reads. So before anyone builds it, this project answers one question:

> **For each type of complaint, can the City's own records tell a resident the truth about their request?**

**Client:** City of New York: 311 and the Office of Technology and Innovation (OTI), which runs it.
**Decision this supports:** for each complaint type, is it ready for a small pilot, does it need a specific data fix first, or should it wait?

## Who cares about this

| Who | What they control | What they get from this project |
|---|---|---|
| 311 / OTI leadership | the 311 system and the decision to build | which complaint types are ready, and what to fix first |
| City agencies (housing HPD, police NYPD, transport DOT, buildings DOB) | the notes they write when they close a request | where their records fail, down to the exact rows |
| 311 call center | the status calls | whether the answer could come from the record instead |
| Residents | the question | an answer that never claims a fix that did not happen |

## How we measure it

**Main measure (KPI): record-answerability.** The share of requests whose record passes all five checks below. A request that passes can be explained to a resident in plain words. **It does not mean the problem was fixed.**

| Check | What it asks |
|---|---|
| A1 Dates | Are the dates in a possible order (not closed before it was opened)? |
| A2 Status | Do the status and the closed date agree? |
| A3 Closing note | Does the agency's note say what happened (if closed) or who acts next (if open)? |
| A4 Target time | Does an open request have a published target time? |
| A5 Record holder | Does 311 hold the status, rather than sending the resident to another website? |

**Safety check (guardrail):** the share of "Closed" requests whose note gives **no evidence the problem was fixed**. This is what an assistant would get wrong if it said "Closed means solved".

**Two readings of the notes.** Some closing notes are vague (for example, one NYPD note says both "no violation found" and "the condition was corrected"). The **loose reading** takes such notes at face value. The **strict reading** counts them as unclear. We report both, because the answer changes a lot.

## What we found (requests created April to June 2026)

| | NYPD (police) | HPD (housing) | DOT (transport) | DOB (buildings) |
|---|---:|---:|---:|---:|
| Requests | 460,240 | 159,275 | 76,000 | 30,604 |
| Record-answerability, loose reading | 98.0% | 96.0% | 60.3% | 66.9% |
| Record-answerability, strict reading | 71.5% | 68.9% | 39.8% | 63.3% |
| Closed, but no evidence it was fixed | 73.8% | 90.8% | 77.2% | 100.0% |

1. **"Closed" usually does not mean "fixed".** For every agency, most closed requests have no evidence of a fix. An assistant reading the status field would mislead residents.
2. **Vague notes decide the outcome.** One NYPD note used on 120,685 requests moves NYPD from 98.0% (loose) to 71.5% (strict). Only the agencies can say what their notes mean.
3. **For a third of DOT requests, 311 does not hold the answer.** The note sends residents to DOT's own website (20,225 requests).
4. **"When will it be fixed?" has no answer in the data.** The due-date field is empty for 99.6% of requests.

## Recommendation

Across the 49 largest complaint types:

| Status | Complaint types | Requests | What it means |
|---|---:|---:|---|
| Ready under both readings | 4 | 12,681 | Can start a small pilot now (for example, NYPD encampment reports) |
| Ready only if the vague notes are confirmed | 27 | 555,224 | Agencies must confirm what their notes mean first |
| Not ready under either reading | 18 | 155,044 | A named data problem must be fixed first (for example, DOT traffic signals: status lives only on DOT's website) |

**So: do not build the assistant yet.** First, the agencies confirm their 7 most-used vague notes, NYPD splits its two-meaning note, and DOT sends its status back into 311. Then this pipeline runs every week and shows which complaint types are ready.

Full evidence and the Known / Unknown / Assumption / Limitation list: [`docs/04_evidence.md`](docs/04_evidence.md). A second run on a fresh download (`output/run_date=2026-09-26/`) gave the same conclusions.

## Sources

| Source | Id | Retrieval | Use |
|---|---|---|---|
| 311 Service Requests from 2020 to Present | `erm2-nwe9` | JSON API, page by page, plus a SQL-style row count (SoQL, the API's query language) | core facts |
| 311 Call Center Inquiry | `wewp-mm3p` | JSON API plus SoQL row count | status-call context |
| 311 Service Level Agreements | `cs9t-e3x8` | JSON file snapshot | response targets (2024) |
| 311 Resolution Satisfaction Survey | `5ijn-vbdv` | JSON file snapshot | resident-view context |

Plus SQL: the cleaned data is loaded into a SQLite database and every metric is a SQL query (`sql/`). Owners, grain, freshness and source-of-truth decisions: [`docs/01_source_map.md`](docs/01_source_map.md).

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
| Dependable pipeline (8) | `run_pipeline.py`, `config/pipeline.json`, `tests/test_pipeline.py`, [`docs/05_gate2_readiness.md`](docs/05_gate2_readiness.md) (the Class 8 "Gate 2" data-readiness checklist) |
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
