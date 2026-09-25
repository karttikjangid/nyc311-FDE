# Closing-text codebook (v1)

Each distinct `resolution_description` string is coded once, on its exact text. Codes describe **what the note says**, not what probably happened.

| Field | Values | Meaning |
|---|---|---|
| `action` | inspected, responded, reviewed, contacted, no_access, violation_issued, summons_issued, arrest, work_order, repaired, referred, duplicate, not_jurisdiction, owner_notified, received_only, redirect, admin_closed, insufficient_info, other | The last thing the agency says it did. |
| `violation_finding` | violation, no_violation, condition_confirmed, not_determined, not_applicable | What the agency says it found. `condition_confirmed` = the problem was seen but no violation language is used. |
| `fix_evidence` | yes, partial, no, unknown | Does the note say the reported condition was corrected? `yes` = says corrected, repaired or restored. `partial` = temporary fix only. `no` = says it is still open, pending, or given time to fix. `unknown` = the note does not say (includes "no violation found" and "no access"). |
| `next_step` | agency, other_party, resident, none | Who the note says acts next. `agency` = the agency (or another agency) will do something. `other_party` = owner, contractor or utility. `resident` = the resident must refile, call or schedule. `none` = nothing stated. A generic "call 311 if the problem persists" alone counts as `resident`. |
| `redirects_elsewhere` | yes, partial, no | `yes` = the status or result is only in another system or a field not published (e.g. "see DOT's website", "Notes to Customer"). `partial` = the note gives an outcome but points elsewhere for key details. |
| `certainty` | high, medium, low | `high` = unambiguous. `medium` = hedged ("may"), self-reported by a third party, or a template whose parts may not all apply. `low` = the note does not say what happened. |

Rules
- Code the text only. Do not use the request's status, agency or complaint type to change a code.
- Never infer a fix from "no violation found".
- If two readings are possible, pick the more cautious one and set certainty to `medium`.
