# Source map

Start point: the resident's question, "Where is my 311 request, and when will it be fixed?"
We broke it into information needs first, then looked for the field and the system that owns each one.

## 1. Information need to source

| # | Information need | Field we use | Source we read | Who owns the truth | Can we trust it for this? |
|---|---|---|---|---|---|
| 1 | Which request is this? | `unique_key` | 311 Service Requests (`erm2-nwe9`) | 311 / OTI | Yes. One row per key in our pull, 0 duplicates. |
| 2 | Which agency has it, and what type is it? | `agency`, `complaint_type`, `descriptor`, `descriptor_2` | `erm2-nwe9` | 311 routes, agency defines types | Yes for routing. `complaint_type` is now called "Problem" in the metadata. |
| 3 | What state is it in now? | `status`, `closed_date` | `erm2-nwe9` | The responding agency. 311 publishes a copy. | Partly. For DOT, 20,225 notes say the real status is on DOT's own website. `status` and `closed_date` disagree on 4,223 rows. |
| 4 | What did the agency do? | `resolution_description` | `erm2-nwe9` | The responding agency | Partly. The metadata defines it as the **last action**, not the outcome. Coded by us into action / finding / fix evidence / next step (`reference/`). |
| 5 | When did it last change? | `resolution_action_updated_date`, `closed_date` | `erm2-nwe9` | The responding agency | Partly. HPD and DOB write some dates at 00:00, so they look earlier than the creation time. |
| 6 | When will it be fixed? | none | none | Nobody publishes this | **No.** `due_date` is empty for 99.6% of rows, and the metadata says it is when the agency should *update* the request, not fix it. |
| 7 | How long should the agency take? | `sla_days` | 311 Service Level Agreements (`cs9t-e3x8`) | 311 / agencies | Context only. "Time the agency needs to address the request", last updated 2024-03-05 although the dataset says it is updated annually. |
| 8 | Are residents asking about status? | `inquiry_name = "Service Request Status"` | 311 Call Center Inquiry (`wewp-mm3p`) | 311 call center | Context only. Agent-handled calls only; the publisher says calls since March 2020 are undercounted; `agency` and `call_resolution` are empty in every Q2 2026 row. |
| 9 | Do residents think it was handled? | `overall_satisfaction`, `dissatisfaction_reason` | 311 Resolution Satisfaction Survey (`5ijn-vbdv`) | OTI | Context only. Self-selected respondents, no request key, month = when the survey was started. |

## 2. Source contracts

| Source | Dataset id | Grain and key | Publisher (metadata) | Update frequency (metadata) | Last updated (at pull) | Retrieval mode | Permitted use in this project |
|---|---|---|---|---|---|---|---|
| 311 Service Requests from 2020 to Present | `erm2-nwe9` | 1 current row per request, `unique_key` | Attribution 311; agency OTI | Daily, automated | 2026-09-25 | Paginated JSON API (keyset on `unique_key`) + SoQL `count(*)` | Core facts, current state at the as-of time |
| 311 Call Center Inquiry | `wewp-mm3p` | 1 agent-handled call, `unique_id` | Attribution 311; agency OTI | Daily, automated | 2026-09-25 | Paginated JSON API + SoQL count | Weekly status-call volume, context |
| 311 Service Level Agreements | `cs9t-e3x8` | 1 rule per agency + problem + detail + additional detail | Attribution 311; agency OTI | Annually, not automated | 2024-03-05 | JSON file snapshot | Response-target match state, context |
| 311 Resolution Satisfaction Survey | `5ijn-vbdv` | 1 survey response, own `unique_key` | OTI | Weekly (data changes daily) | 2026-09-21 | JSON file snapshot | Agency-level context only |

Cohort: requests created 2026-04-01 to 2026-06-30 (969,004 rows). Survey: responses from 2025 on. Calls: same dates as the cohort.

## 3. Source-of-truth decisions

| Fact | Tentative system of record | Why | What we did |
|---|---|---|---|
| Request identity and routing | 311 (OTI) | 311 creates the request and assigns the agency | Used as is |
| Current status for DOT requests | DOT's own system, **not** 311 | DOT's closing note sends residents to DOT's website for 20,225 requests | Marked A5 FAIL (record held elsewhere). We did not try to scrape DOT. |
| What the agency did | The agency (HPD, NYPD, DOT, DOB) | Agencies write the closing notes | Coded the text, flagged as our reading, needs agency sign-off |
| Whether the problem was physically fixed | Nobody publishes it | No field records a physical fix; notes mention it only sometimes | Reported as "fix evidence yes / no / unknown", never inferred from Closed |
| Expected time | Agency commitments (2024 table) | Only published target; not a repair date | Match state only (MATCHED / AMBIGUOUS / NOT_MANAGED_BY_311 / UNMATCHED) |

A newer timestamp does not make a source the owner. Open data is a daily copy, so a production assistant would need the 311 CRM and the agency systems, not this dataset.

## 4. Gaps that change scope

- **No history.** The dataset keeps one current row per request. We cannot see what a resident would have been told on an earlier day. We report current state at one as-of time only.
- **No "when fixed" field.** No source can answer the second half of the resident's question.
- **Missing links.** Calls, survey answers and duplicate requests carry no key back to the request (duplicate notes say "the original complaint is being addressed" without its number).
- **Publication lag unknown.** We can see when the dataset was refreshed, not how far behind the agency systems it is.

## 5. Minimum fields the pipeline pulls

`unique_key, created_date, closed_date, due_date, resolution_action_updated_date, agency, agency_name, complaint_type, descriptor, descriptor_2, status, resolution_description, open_data_channel_type, borough, community_board, incident_zip, location_type`. No names, addresses or free-text complaints from residents.
