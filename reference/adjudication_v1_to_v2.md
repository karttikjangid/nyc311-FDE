# Adjudication: mapping v1 to v2

Coder 1 wrote `closing_text_map_v1.csv`. Coder 2 (a separate agent that did not see v1) wrote `closing_text_map_coder2.csv` from `codebook.md` and the note texts alone. Agreement below is v1 vs coder 2, before any change. The pipeline uses v2.

## Changes made in v2

| Hash | Agency | Rows (Q2) | Field | v1 | v2 | Reason |
|---|---|---:|---|---|---|---|
| `0790b55068b1f221` | HPD | 7088 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `118680b0bd68f453` | HPD | 5331 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `bbed8069ef2fd857` | HPD | 1701 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `df75584745e82369` | NYPD | 120685 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `f73dba4136ecd5f2` | NYPD | 116873 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `2c08ac6d5aacf6d1` | NYPD | 74973 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `0c98b296ce96f0df` | NYPD | 61131 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `8cb78effa85af149` | NYPD | 5304 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `7d715154e8d9d6ac` | NYPD | 3 | next_step | none | resident | Codebook rule: 'call 311 / file again if it persists' counts as resident. Coder 1 broke its own rule; coder 2 applied it. |
| `d148265a9ea0ea24` | HPD | 25416 | action | no_access | other | Note says the inspection could not be completed, not that access failed. Coder 1 over-read it. |
| `d148265a9ea0ea24` | HPD | 25416 | redirects_elsewhere | no | partial | The reason is only available by phone from HPD. |
| `d148265a9ea0ea24` | HPD | 25416 | certainty | high | medium | Reason for the failed inspection is not stated. |
| `31aa934ecb8644ed` | HPD | 10712 | fix_evidence | unknown | no | Note says the original complaint is still open, which the codebook codes as 'no'. |
| `9fa2f87ecd8202b8` | DOT | 2835 | certainty | high | medium | 'completed the request OR corrected the condition' is hedged. |
| `e6e21e65ec8b6339` | DOB | 10904 | violation_finding | no_violation | not_determined | 'No further action necessary' does not state that no violation was found. |
| `9e34d851caa27ea6` | DOB | 238 | violation_finding | no_violation | not_determined | Same wording as above. |
| `0790b55068b1f221` | HPD | 7088 | certainty | high | medium | Fix reported by an occupant, not verified by inspection (codebook: third-party report = medium). |
| `bbed8069ef2fd857` | HPD | 1701 | certainty | high | medium | Correction verified through a tenant, not by inspection. |
| `62bb642af3725422` | DOT | 3597 | certainty | high | medium | 'meets its standards and/or there is a valid permit' leaves the finding open. |

## Disagreements kept as v1

| Hash | Agency | Rows (Q2) | Field | Disagreement | Decision |
|---|---|---:|---|---|---|
| `df75584745e82369` | NYPD | 120685 | certainty | coder 1 medium, coder 2 high | Kept medium. The template states both 'no criminal violation' and 'condition corrected' on 120,685 requests; whether each case was corrected cannot be checked. The strict KPI reading shows the effect. |
| `f73dba4136ecd5f2` | NYPD | 116873 | certainty | coder 1 high, coder 2 medium | Kept high. 'With the information available' hedges the evidence, but what the police did and found is stated plainly. |
| `b37290ec8cd1f47a` | DOB | 5993 | certainty | coder 1 low, coder 2 high | Kept low. 'Reviewed this complaint and closed it' gives no result. |
| `8b83a941dce28fee` | HPD | 5949 | next_step | coder 1 agency, coder 2 resident | Kept agency. The note names both; HPD's own follow-up (call or inspect) is the step that changes the record. |
| `b7c15cf612b149bc` | DOT | 6964 | certainty | coder 1 medium, coder 2 high | Kept medium. 'The original complaint is being addressed' without the original's key. |

Other disagreements (the split between `not_applicable` and `not_determined`, and between `violation_issued`, `owner_notified` and `work_order` for DOT notices) come from codebook wording. They do not change any KPI check. Codebook v2 should define these pairs more tightly.

## Agreement before adjudication (v1 vs coder 2, 110 notes)

| Field | Agreement (notes) | Agreement (weighted by requests) | Cohen's kappa |
|---|---:|---:|---:|
| action | 81.8% | 91.5% | 0.80 |
| violation_finding | 79.1% | 94.6% | 0.69 |
| fix_evidence | 94.5% | 98.1% | 0.87 |
| next_step | 84.5% | 44.7% | 0.78 |
| redirects_elsewhere | 92.7% | 95.4% | 0.76 |
| certainty | 77.3% | 56.5% | 0.47 |

`certainty` is the weakest field (kappa 0.47, below our 0.60 bar), so validation rule R18 is WARN. This is why the evidence reports a strict reading next to the loose one. The low request-weighted agreement on `next_step` came from one coder-1 error on large NYPD templates, fixed in v2.
