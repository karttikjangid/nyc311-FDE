# Gate 2: data readiness (generated)

Run date 2026-09-26, snapshot `20260925T175230Z`, as-of 2026-09-25 13:52:30 (assumed America/New_York).

| Decision | Result |
|---|---|
| Weekly evidence reporting | **READY (with warnings)** |
| Live answers to residents | **NOT READY** (blocked by R08, R09, R10, R14, R15, R18, R20, R23, R25) |

| Rule | Check | Weekly reporting | Live answer | Blocking |
|---|---|---|---|---|
| R01 | Retrieval count matches source count | PASS | PASS | yes |
| R02 | Raw files unchanged since retrieval | PASS | PASS | yes |
| R03 | Required columns present | PASS | PASS | yes |
| R04 | Full SLA hierarchy available | PASS | PASS | no |
| R05 | One row per request | PASS | PASS | yes |
| R06 | Timestamps parse | PASS | PASS | yes |
| R07 | Rows inside the requested window | PASS | PASS | yes |
| R08 | Snapshot fresh enough | PASS | UNKNOWN | yes |
| R09 | Event order is possible | WARN | FAIL | no |
| R10 | Status and closed date agree | WARN | FAIL | no |
| R11 | Closure time has hour precision | WARN | WARN | no |
| R12 | No timestamps after the snapshot | PASS | PASS | no |
| R13 | Status values are known | PASS | PASS | no |
| R14 | Closing note present | WARN | FAIL | no |
| R15 | Closing note text intact | WARN | FAIL | no |
| R16 | Mapping file is valid | PASS | PASS | yes |
| R17 | Mapping covers the focus-agency notes | PASS | PASS | yes |
| R18 | Mapping agrees with an independent coder | WARN | UNKNOWN | no |
| R19 | SLA units understood | PASS | PASS | no |
| R20 | SLA reference is current | WARN | FAIL | no |
| R21 | SLA match is unambiguous | WARN | WARN | no |
| R22 | Joins do not duplicate rows | PASS | PASS | yes |
| R23 | Timezone of timestamps | UNKNOWN | UNKNOWN | no |
| R24 | Status calls attributable to an agency | WARN | WARN | no |
| R25 | Survey represents all requests | WARN | FAIL | no |
| R26 | Model reconciles to cleaned rows | PASS | PASS | yes |

Pipeline behaviour evidenced in this run: raw pages verified by SHA-256 (R02), counts reconciled (R01, R26),
joins checked for fan-out (R22), output written to a temp folder and swapped in atomically.
