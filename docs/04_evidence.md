# Evidence and decision

All numbers come from `output/run_date=2026-09-25/` (snapshot `20260925T112431Z_initial`, as-of 2026-09-25 07:24 New York time, assumed). Cohort: 969,004 requests created 2026-04-01 to 2026-06-30. Focus agencies: HPD, NYPD, DOT, DOB (726,119 requests).

## 1. Evidence table

| Metric | Type | NYPD | HPD | DOT | DOB |
|---|---|---:|---:|---:|---:|
| Requests | | 460,240 | 159,275 | 76,000 | 30,604 |
| **Record-answerability (all five checks pass)** | Project KPI | 98.0% | 96.0% | 60.3% | 66.9% |
| Same, strict reading of the notes | KPI sensitivity | 71.5% | 68.9% | 39.8% | 63.3% |
| Closed but the note gives no evidence of a fix | Guardrail (outcome) | 73.8% | 90.8% | 77.2% | 100.0% |
| Open requests whose note says who acts next | Supporting (next step) | 8 of 9 | 99.9% of 5,151 | 60.3% of 4,361 | 61.5% of 3,759 |
| Most common agency action | Supporting (intervention) | responded, no violation found (82.3%) | inspected (29.8%) | note sends resident to DOT or 311 for status (27.3%) | inspected (35.6%) |
| Main reason a request is not answerable | Diagnostic | A5 note points elsewhere (2.0% of requests) | A5 note points elsewhere (2.5%) | A5 status held by DOT (32.2%) | A3 note unreadable (20.8%) |

Focus agencies combined: 92.3% answerable, 67.3% under the strict reading, 1.8% UNKNOWN, 5.9% FAIL.

Context, not per-request metrics:
- 20,389 agent-handled "Service Request Status" calls in the same 14 weeks, about 1,500 to 1,750 a week against 70,000 to 80,000 new requests a week. The publisher says this dataset undercounts calls.
- Survey responses begun April to September 2026 (self-selected): 76.8% of NYPD respondents and 59.0% of HPD respondents disagree that their request was handled well. 44.5% of HPD respondents pick "the Agency did not correct the issue".

How to read the KPI: **answerable means the record can tell the resident, in plain words, what happened or what happens next. It does not mean the problem was fixed.** The guardrail row shows how far apart those two are. The strict reading treats every note that either coder found hedged (certainty "medium") as UNKNOWN.

## 2. What the numbers say

1. **Reading `status` would mislead residents.** For NYPD, HPD, DOT and DOB, between 74% and 100% of Closed requests carry no evidence in the note that the condition was corrected. An assistant that says "Closed, so it's resolved" would be wrong for most of them.
2. **The answer depends on how the closing notes are read, and only the agencies can settle that.** Under the loose reading, 31 of 49 large complaint types (567,905 requests) would qualify for a pilot. Under the strict reading, 4 do (12,681 requests). The blind second coder is what exposed this: before adjudication our own coding put HPD at 90.4% strict; after it, 68.9%.
3. **A third of HPD requests end without a completed inspection.** 16.8% close with "could not get access" and 16.0% with "unable to complete the inspection", so residents learn why nothing happened, not that it was fixed. HPD's records are otherwise the clearest: 99.9% of open HPD requests state a next step.
4. **One NYPD template sets NYPD's score.** 120,685 NYPD requests close with a note that says both "no criminal violation existed" and "the condition was corrected". Read at face value, NYPD scores 98.0%. Treated as uncertain, 71.5%.
5. **DOT cannot be answered from 311 for a third of its requests.** 33.1% of DOT notes point elsewhere for the status: DOT's website (20,225 requests), a "Notes to Customer" field that is not published (4,414) or a call to 311 (485). For traffic signals and street lights, 94% to 98% of requests stop at this check.
6. **DOB records disagree with themselves.** 3,759 DOB requests are Open or Assigned but already have a closed date, and 89% of DOB closure times are exactly midnight.
7. **"When will it be fixed?" has no answer in the data.** `due_date` is empty for 99.6% of requests. The only published targets are a 2024 table of response times, and they match cleanly for 75.5% of requests (the rest are ambiguous, unmatched or "not managed by 311").

## 3. Proposed decision (owner: 311/OTI leadership with each agency)

The rule uses the strict reading so it stays conservative: 90%+ answerable = candidate, 60 to 90% = fix the named blocker first, below 60% = hold. The loose-reading decision is shown beside it. Full list: `output/run_date=2026-09-25/evidence_table.md` and `kpi_by_complaint_type.csv`.

| Decision (strict) | Complaint types | Requests | Examples |
|---|---:|---:|---|
| Candidate for a **measurement pilot** | 4 | 12,681 | NYPD encampment; DOB electrical, emergency response team, real-time enforcement |
| **Fix the blocker first** | 28 | 530,888 | most HPD housing conditions and NYPD parking and noise types; the blocker is the note wording (A3) |
| **Hold** | 17 | 179,380 | HPD heat/hot water; DOT signals, street lights, sidewalks; NYPD street and commercial noise |
| Of which **hold under both readings** | 7 | 36,033 | DOT traffic signal, street light, outdoor dining, parking meters (status held by DOT); DOB elevator, building/use, SPIT |

A pilot here means reading back the coded outcome to residents or call-center agents and measuring whether repeat status calls fall. It never means telling a resident "fixed" without fix evidence.

What we recommend next, in order:
1. **Agencies confirm the meaning of their hedged closing notes.** 21 notes are coded "medium" certainty and cover 184,184 requests; 7 of them cover 95% of those requests (one NYPD template alone covers 120,685). Confirming these few notes decides whether 4 or 31 complaint types are ready.
2. NYPD splits the combined "no violation / condition corrected" template into two notes.
3. DOT publishes status back into 311 for signals and street lights, or 311 links to the DOT record by key.
4. OTI adds to the 311 feed: structured outcome fields (action, violation found, condition corrected), a status-history table, a per-request target date, and a request key on call and survey records.
5. Re-run this pipeline weekly and track the KPI per complaint type before anyone builds an AI assistant.

## 4. Known / Unknown / Assumption / Limitation

**Known (measured in this data)**
- 969,004 requests pulled; count matches the API's own count; 0 duplicate keys; raw pages hashed.
- 95.5% of requests are Closed; 99.6% have no `due_date`.
- 2,261 requests have a real ordering error (closed or updated before creation); 8,514 more look like errors but are date-only timestamps.
- 4,225 requests have a status that disagrees with the closed date; 26,087 have no usable closing note; 24,899 notes have broken character encoding and 28,245 HPD notes are cut off at 500 characters.
- 20,225 DOT notes point to DOT's website for status.

**Unknown (the data cannot tell us)**
- Whether any Closed request was physically fixed, beyond what the note says.
- What a resident was told on any past day (no status history).
- How far the open data lags the agency systems.
- Which request a status call or survey answer is about.
- Whether the 2024 SLA table still applies, and whether its "days" are calendar or business days.

**Assumptions (ours, need an owner)**
- Timestamps are New York local time (R23).
- Our coding of 110 closing notes (mapping v2) is correct. A blind second coder agreed on 77% to 95% of notes per field (kappa 0.47 to 0.87, certainty lowest); 19 codes changed after adjudication (`reference/adjudication_v1_to_v2.md`). Agency sign-off is still needed.
- A 00:00 timestamp on the creation day means "date only", not "before creation".
- SLA days are calendar days x 24 hours.
- The 90% / 60% decision thresholds.

**Limitations**
- One quarter of requests, one snapshot: current state only, no trend.
- Notes coded only for HPD, NYPD, DOT and DOB; other agencies get the checks that need no coding.
- Survey and call data are context; they cannot validate any single request.
- Open data stands in for the 311 CRM. A production answer would need the CRM and agency systems.

## 5. Live re-run

On 2026-09-25 at 17:52 UTC the pipeline pulled a fresh snapshot itself (`--source live`, published as `output/run_date=2026-09-26/`). All four datasets came through keyset pagination with counts matching the API exactly (969,004 requests, 950,999 calls, 3,563 SLA rules, 275,467 survey responses), and one read timeout was retried automatically. This pull added `descriptor_2`, the third level of the SLA key: clean response-target matches rose from 75.5% to 84.6% and ambiguous matches fell from 131,223 to 42,937. The KPI moved from 92.3% to 92.6% (strict reading unchanged at 67.3%). The conclusions above do not change.
