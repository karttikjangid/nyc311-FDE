# NYC 311 Q2 2026 raw profile

Raw descriptive inspection only. Dates without an offset were interpreted as UTC for comparisons; source strings remain unchanged.

## Acquisition

- Main dataset: `erm2-nwe9` — 311 Service Requests from 2020 to Present
- `rowsUpdatedAt`: `1790300423`; ISO UTC: `2026-09-25T01:40:23+00:00`
- Query window: `created_date >= 2026-04-01T00:00:00 AND created_date < 2026-07-01T00:00:00`
- Raw metadata: `data/raw/metadata/erm2-nwe9_views.json`

## Pre-pull counts

- Total: **969004**

### By agency

| agency | count |
| --- | --- |
| DCWP | 5735 |
| DEP | 56619 |
| DHS | 15383 |
| DOB | 30604 |
| DOHMH | 22995 |
| DOT | 76000 |
| DPR | 46360 |
| DSNY | 80490 |
| EDC | 3090 |
| HPD | 159275 |
| NYC311-PRD | 294 |
| NYPD | 460240 |
| OOS | 1174 |
| OTI | 85 |
| TLC | 10660 |

### By status

| status | count |
| --- | --- |
| Assigned | 3565 |
| Closed | 925508 |
| In Progress | 29742 |
| Open | 7984 |
| Pending | 1660 |
| Started | 526 |
| Unspecified | 19 |

## Main pull

- Start UTC: `2026-09-25T11:24:31.783964+00:00`; end UTC: `2026-09-25T11:38:09.575904+00:00`
- Page count: **20**; rows per page: `[50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 50000, 19004]`
- Total rows: **969004**; expected: **969004**; match: **True**; difference: **0**
- Duplicate `unique_key` occurrences across pages: **0**
- Query URL template: `https://data.cityofnewyork.us/resource/erm2-nwe9.json?%24select=unique_key%2Ccreated_date%2Cclosed_date%2Cdue_date%2Cresolution_action_updated_date%2Cagency%2Cagency_name%2Ccomplaint_type%2Cdescriptor%2Cstatus%2Cresolution_description%2Copen_data_channel_type%2Cborough%2Ccommunity_board%2Cincident_zip%2Clocation_type&%24where=created_date+%3E%3D+%272026-04-01T00%3A00%3A00%27+AND+created_date+%3C+%272026-07-01T00%3A00%3A00%27&%24limit=50000&%24offset=%7Boffset%7D&%24order=unique_key`

## Raw profile

- Rows successfully loaded into pandas as strings: **969004**
- Columns: `unique_key`, `created_date`, `closed_date`, `due_date`, `resolution_action_updated_date`, `agency`, `agency_name`, `complaint_type`, `descriptor`, `status`, `resolution_description`, `open_data_channel_type`, `borough`, `community_board`, `incident_zip`, `location_type`

### Nulls

| column | null count | null % |
| --- | --- | --- |
| unique_key | 0 | 0.00% |
| created_date | 0 | 0.00% |
| closed_date | 39275 | 4.05% |
| due_date | 965321 | 99.62% |
| resolution_action_updated_date | 15335 | 1.58% |
| agency | 0 | 0.00% |
| agency_name | 0 | 0.00% |
| complaint_type | 0 | 0.00% |
| descriptor | 0 | 0.00% |
| status | 0 | 0.00% |
| resolution_description | 18284 | 1.89% |
| open_data_channel_type | 0 | 0.00% |
| borough | 0 | 0.00% |
| community_board | 0 | 0.00% |
| incident_zip | 8611 | 0.89% |
| location_type | 138019 | 14.24% |

### Top 30: agency

| agency | count |
| --- | --- |
| NYPD | 460240 |
| HPD | 159275 |
| DSNY | 80490 |
| DOT | 76000 |
| DEP | 56619 |
| DPR | 46360 |
| DOB | 30604 |
| DOHMH | 22995 |
| DHS | 15383 |
| TLC | 10660 |
| DCWP | 5735 |
| EDC | 3090 |
| OOS | 1174 |
| NYC311-PRD | 294 |
| OTI | 85 |

### Top 30: status

| status | count |
| --- | --- |
| Closed | 925508 |
| In Progress | 29742 |
| Open | 7984 |
| Assigned | 3565 |
| Pending | 1660 |
| Started | 526 |
| Unspecified | 19 |

### Top 30: open_data_channel_type

| open_data_channel_type | count |
| --- | --- |
| ONLINE | 443543 |
| PHONE | 232228 |
| MOBILE | 203571 |
| UNKNOWN | 89173 |
| OTHER | 489 |

### Top 30: borough

| borough | count |
| --- | --- |
| BROOKLYN | 303913 |
| QUEENS | 248808 |
| MANHATTAN | 191514 |
| BRONX | 185358 |
| STATEN ISLAND | 38206 |
| Unspecified | 1205 |

### Top 30: complaint_type

| complaint_type | count |
| --- | --- |
| Illegal Parking | 164499 |
| Noise - Residential | 102229 |
| Noise - Street/Sidewalk | 56500 |
| Blocked Driveway | 47435 |
| Street Condition | 38479 |
| HEAT/HOT WATER | 33764 |
| UNSANITARY CONDITION | 32847 |
| Water System | 20826 |
| Abandoned Vehicle | 20601 |
| PLUMBING | 18978 |
| Dirty Condition | 17840 |
| Noise - Commercial | 17798 |
| Noise | 16972 |
| Noise - Vehicle | 16218 |
| PAINT/PLASTER | 15886 |
| Damaged Tree | 13554 |
| Encampment | 13550 |
| DOOR/WINDOW | 12342 |
| General Construction/Plumbing | 11619 |
| Traffic Signal Condition | 11581 |
| Homeless Person Assistance | 11239 |
| GENERAL | 10260 |
| Illegal Dumping | 10090 |
| Derelict Vehicles | 9970 |
| Maintenance or Facility | 9869 |
| Missed Collection | 9619 |
| WATER LEAK | 9479 |
| Sewer | 9126 |
| Street Light Condition | 8782 |
| Overgrown Tree/Branches | 8669 |

### Top 50: resolution_description

Counts are for full, unmodified strings; display text is truncated to 150 characters.

| resolution_description (first 150 chars) | count |
| --- | --- |
| The New York City Police Department responded to the complaint and their investigation determined that no criminal violation existed. The condition wa | 120685 |
| The New York City Police Department responded to the complaint and with the information available observed no evidence of a criminal violation at that | 116873 |
| The New York City Police Department responded to the complaint and observed no criminal violation upon their arrival. If the problem persists, please  | 74973 |
| The New York City Police Department responded to the complaint and their investigation determined that police action was not necessary. If the problem | 61131 |
| The New York City Police Department responded to the complaint and their investigation determined that a violation of law occurred. Police issued a su | 54476 |
| HPD conducted an inspection of this complaint. The conditions observed by the inspector did not violate the housing laws enforced by HPD. The complain | 32852 |
| HPD inspected this condition so the complaint has been closed. Violations were issued. The law provides the property owner time to correct the conditi | 28245 |
| HPD attempted to conduct an inspection in response to this complaint, but was unable to complete the inspection. Please submit a new service request w | 25416 |
| An HPD Inspector was not able to gain access to inspect this complaint. The Inspector left a card at the time of the inspection and a letter was sent  | 20425 |
| (null) | 18284 |
| Service Request status for this request is available on the Department of Transportationâs website. Please click the âLearn Moreâ link below. | 16413 |
| The Department of Sanitation investigated this complaint and found no condition at the location. | 14577 |
| The Department of Transportation inspected this complaint and repaired the problem. | 12305 |
| The Department of Environmental Protection determined that this complaint is a duplicate of a previously filed complaint. The original complaint is be | 12164 |
| The New York City Police Department responded to the complaint but officers were unable to gain entry into the premises. If the problem persists, plea | 11935 |
| The Department of Buildings investigated this complaint and determined that no further action was necessary. | 10904 |
| This complaint is a duplicate of a building-wide condition already reported by another tenant.  The original complaint is still open, and HPD may only | 10712 |
| The Department of Environmental Protection (DEP) didn't observe a violation of the NYC Air or Noise Code at the time of inspection and couldn't issue  | 9145 |
| The Department of Sanitation cleaned the location. | 8593 |
| N/A | 7803 |
| The Department of Housing Preservation and Development inspected the following conditions. No violations were issued. The complaint has been closed. | 7279 |
| HPD responded to a complaint of no heat or hot water in the building. An occupant of the building confirmed heat and hot water had been restored when  | 7088 |
| The mobile outreach response team went to the location provided but could not find the individual that you reported. | 7070 |
| The Department of Transportation determined that this complaint is a duplicate of a previously filed complaint. The original complaint is being addres | 6964 |
| NYC Parks has completed the requested work order and corrected the problem. | 6732 |
| The Department of Environment Protection inspected your complaint but could not find the problem you reported. If the condition persists, please call  | 6517 |
| The Department of Sanitation collected the requested items. | 6344 |
| The Department of Sanitation investigated this complaint and found no violation at the location. | 6321 |
| The Department of Buildings reviewed this complaint and closed it. If the problem still exists, please call 311 and file a new complaint. If you are o | 5993 |
| The following complaint conditions are still open. HPD has already attempted to notify the property owner that the condition exists; the tenant should | 5949 |
| The Taxi and Limousine Commission (TLC) has received your complaint. Within 30 days, the TLC representative who will be handling your case will contac | 5575 |
| Your complaint has been received but does not fall under the jurisdiction of the New York City Police Department.  Please contact your local precinct  | 5384 |
| The Department of Sanitation investigated this complaint and issued a Notice of Violation. | 5351 |
| HPD called the telephone number on file for this complaint.  Someone at that number indicated that the condition was corrected. The complaint has been | 5331 |
| The New York City Police Department responded to the complaint and observed no encampment at the noted location. If the problem persists, please conta | 5304 |
| NYC Parks performed the work necessary to correct the condition. | 5186 |
| The Department of Transportation inspected and has requested the Department of Environmental Protection address the issue. The condition will be re-in | 5104 |
| NYC Parks visited the site and inspected the condition. No work is necessary at this time. | 4995 |
| The Department of Housing Preservation and Development was not able to gain access to your apartment or others in the building to inspect for a lack o | 4268 |
| NYC Parks created a work order for the tree condition.  Please note that addressing this work can take up to a year or more depending on the higher pr | 4158 |
| The New York City Police Department responded to the complaint and observed an encampment at the noted location. The complaint has been referred to th | 4153 |
| The NYC Health Department has responded to your service request.  Restaurant inspection information can be found online at www.nyc.gov/health/abceats. | 3954 |
| NYC Parks reviewed this request and will visit the location to investigate the condition.  Under NYC Parksâ Tree Risk Management Program, all trees  | 3935 |
| The Department of Transportation inspected the condition you reported. You can find additional information in the "Notes to Customer" field. | 3887 |
| The Department of Housing Preservation and Development conducted or attempted to conduct an inspection.  More information about inspection results can | 3882 |
| Service Request status for this request is available on the Department of Transportation's website. Please click the "Learn More" link below. | 3812 |
| The Police Department reviewed your complaint and provided additional information below. | 3682 |
| The Department of Transportation inspected the condition you reported and found that the condition meets its standards and/or there is a valid permit  | 3676 |
| The Department of Buildings investigated this complaint and issued an Office of Administrative Trials and Hearings (OATH) summons. | 3453 |
| The Department of Environmental Protection investigated this complaint and shut the running hydrant. | 3389 |

### Date fields

| field | min UTC | max UTC | exact midnight | before 2010 | after pull end | non-null | unparseable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| created_date | 2026-04-01T00:00:00+00:00 | 2026-06-30T23:59:53+00:00 | 140 | 0 | 0 | 969004 | 0 |
| closed_date | 2026-01-18T14:41:00+00:00 | 2026-09-23T19:52:34+00:00 | 30797 | 0 | 0 | 929729 | 0 |
| due_date | 2026-04-07T06:45:42+00:00 | 2026-08-25T16:36:14+00:00 | 0 | 0 | 0 | 3683 | 0 |
| resolution_action_updated_date | 2022-11-05T10:07:55+00:00 | 2026-09-24T00:07:47+00:00 | 50942 | 0 | 0 | 953669 | 0 |

### Date/status inconsistencies

| condition | count |
| --- | --- |
| closed_date < created_date | 170 |
| closed_date not null but status != Closed | 4223 |
| closed_date null but status == Closed | 2 |
| due_date < created_date | 0 |
| resolution_action_updated_date < created_date | 10765 |

### due_date null by agency

| agency | rows | due_date null | due_date null % |
| --- | --- | --- | --- |
| DCWP | 5735 | 5735 | 100.00% |
| DEP | 56619 | 56619 | 100.00% |
| DHS | 15383 | 15383 | 100.00% |
| DOB | 30604 | 30604 | 100.00% |
| DOHMH | 22995 | 22995 | 100.00% |
| DOT | 76000 | 76000 | 100.00% |
| DPR | 46360 | 46360 | 100.00% |
| DSNY | 80490 | 76807 | 95.42% |
| EDC | 3090 | 3090 | 100.00% |
| HPD | 159275 | 159275 | 100.00% |
| NYC311-PRD | 294 | 294 | 100.00% |
| NYPD | 460240 | 460240 | 100.00% |
| OOS | 1174 | 1174 | 100.00% |
| OTI | 85 | 85 | 100.00% |
| TLC | 10660 | 10660 | 100.00% |

### RAW, NOT A METRIC: closed_date minus created_date by agency

Hours on rows where both timestamps parse and `closed_date >= created_date`. No status or quality interpretation is implied.

| agency | eligible rows | median hours | 90th percentile hours |
| --- | --- | --- | --- |
| DCWP | 5725 | 727.096 | 1001.711 |
| DEP | 55613 | 23.617 | 242.450 |
| DHS | 14517 | 6.312 | 122.409 |
| DOB | 30604 | 121.659 | 1567.926 |
| DOHMH | 21505 | 294.844 | 1440.329 |
| DOT | 71864 | 51.108 | 432.573 |
| DPR | 31082 | 113.017 | 1525.301 |
| DSNY | 79226 | 28.450 | 122.213 |
| HPD | 154126 | 147.168 | 756.086 |
| NYC311-PRD | 294 | 29.737 | 135.245 |
| NYPD | 460239 | 1.460 | 6.823 |
| OOS | 1050 | 1469.867 | 2177.133 |
| OTI | 80 | 525.312 | 985.109 |
| TLC | 3634 | 147.253 | 1453.525 |

## Related 311 datasets

Catalog response: `data/raw/catalog/311_limit100.json`

| role | id | name | description | update frequency | row count shown | one row represents | Q2 pull |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 311 call center / inquiry | wewp-mm3p | 311 Call Center Inquiry | Agent-handled calls to the City's 311 information line, with date, time, topic and call resolution. The first saved Q2 page contains the inquiry_name 'Service Request Status'. The publisher warns that activity since March 2020 does not fully represent all agent-handled calls. | Daily | Not shown in catalog or views metadata | An inquiry to the 311 call center handled by a 311 agent (publisher row label) | Pulled 950999 rows in 20 raw pages; matches pre-pull window count |
| 311 resolution satisfaction survey | 5ijn-vbdv | 311 Resolution Satisfaction Survey | Customer feedback on how a City agency resolved a service request; response time is aggregated to survey year and month to protect anonymity. | Weekly (data change frequency: Daily) | Not shown in catalog or views metadata | One survey response (publisher description and row label) | Not pulled: no date column; only numeric year and month |
| 311 service level targets | cs9t-e3x8 | 311 Service Level Agreements | Time commitments City agencies have made for responding to assigned 311 service requests. | Annually | Not shown in catalog or views metadata | An agency and service-request problem/detail combination with its SLA days (inferred from columns) | Not pulled: no date column |

- `wewp-mm3p` metadata: `data/raw/related/wewp-mm3p/metadata_views.json`; Q2 count: `data/raw/related/wewp-mm3p/total.json`; manifest: `data/raw/related/wewp-mm3p/created_2026Q2/_manifest.json`
- `5ijn-vbdv` metadata: `data/raw/related/5ijn-vbdv/metadata_views.json`
- `cs9t-e3x8` metadata: `data/raw/related/cs9t-e3x8/metadata_views.json`

## Problems

- **profile**: closed_date < created_date: 170 — `data/raw/service_requests/created_2026Q2`
- **profile**: closed_date null but status == Closed: 2 — `data/raw/service_requests/created_2026Q2`
- **profile**: closed_date not null but status != Closed: 4223 — `data/raw/service_requests/created_2026Q2`
- **profile**: resolution_action_updated_date < created_date: 10765 — `data/raw/service_requests/created_2026Q2`
- **acquisition_retries**: 1 retry event(s); see log for status, delay, and request details — `logs/acquire_20260925T112431Z.log`

## Deliverables checklist

- done — nyc311/acquire/*.py (rerunnable)
- done — nyc311/data/raw/metadata/*
- done — nyc311/data/raw/counts/*
- done — nyc311/data/raw/service_requests/created_2026Q2/page_*.json.gz + _manifest.json
- done — nyc311/data/raw/<other datasets>/* (if found)
- done — nyc311/reports/raw_profile.md
- done — nyc311/logs/acquire_<UTC timestamp>.log

## Pull 2

Raw reference-dataset pulls and descriptive counts only. No values were cleaned or changed.

### A. 311 Service Level Agreements (`cs9t-e3x8`)

- Count response: `data/raw/related/cs9t-e3x8/full_count.json`
- Rows received: **3563**; expected: **3563**; match: **True**
- Pages: **1**; manifest: `data/raw/related/cs9t-e3x8/full/_manifest.json`

Distinct `agency` values: `Administration for Children's Services`, `Department for the Aging`, `Department of Buildings`, `Department of Consumer and Worker Protection`, `Department of Education`, `Department of Environmental Protection`, `Department of Finance`, `Department of Health and Mental Hygiene`, `Department of Homeless Services`, `Department of Housing Preservation and Development`, `Department of Parks and Recreation`, `Department of Records and Information Services`, `Department of Sanitation`, `Department of Transportation`, `Economic Development Corporation`, `Human Resources Administration`, `NYC Emergency Management`, `New York City Police Department`, `Office of Technology and Innovation`, `Small Business Services`, `Taxi and Limousine Commission`

#### First 20 rows in raw page order

```jsonl
{"agency": "Administration for Children's Services", "problem": "ACS Literature Request", "sla_days": "7 days"}
{"agency": "Department for the Aging", "problem": "Case Management Agency Complaint", "problem_details": "N/A", "additional_details": "N/A", "sla_days": "14 days"}
{"agency": "Department for the Aging", "problem": "Home Delivered Meal - Missed Delivery", "problem_details": "N/A", "additional_details": "N/A", "sla_days": "3 days"}
{"agency": "Department for the Aging", "problem": "Legal Services Provider Complaint", "problem_details": "N/A", "additional_details": "N/A", "sla_days": "14 days"}
{"agency": "Department of Buildings", "problem": "Abandoned Building", "problem_details": "Not Closed/Sealed", "additional_details": "N/A", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Adult Establishment", "problem_details": "Zoning Violation", "additional_details": "Near Church/School", "sla_days": "40 days"}
{"agency": "Department of Buildings", "problem": "Adult Establishment", "problem_details": "Zoning Violation", "additional_details": "Illegal Business", "sla_days": "40 days"}
{"agency": "Department of Buildings", "problem": "Adult Establishment", "problem_details": "Zoning Violation", "additional_details": "Illegal Hours", "sla_days": "40 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Billboard", "additional_details": "Inappropriate Picture", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Billboard", "additional_details": "Inappropriate Symbol", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Billboard", "additional_details": "Inappropriate Wording", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Billboard", "additional_details": "No Permit", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Billboard", "additional_details": "Too Big", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Flexible Fabric", "additional_details": "No Permit", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Poster", "additional_details": "No Permit", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Poster", "additional_details": "Too Big", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Poster", "additional_details": "Inappropriate Wording", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Poster", "additional_details": "Inappropriate Symbol", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Advertising Sign", "problem_details": "Poster", "additional_details": "Inappropriate Picture", "sla_days": "60 days"}
{"agency": "Department of Buildings", "problem": "Awning/Canopy/Marquee", "problem_details": "Illegal", "additional_details": "Commercial", "sla_days": "60 days"}
```

#### `sla_days` values

| sla_days | count |
| --- | --- |
| 4 days | 920 |
| SLA Not Managed by 311 | 761 |
| 14 days | 325 |
| 7 days | 230 |
| 3 days | 176 |
| 30 days | 163 |
| 37 days | 135 |
| 10 days | 131 |
| 8 days | 105 |
| 8 hours | 97 |
| 5 days | 96 |
| 2 days | 93 |
| 40 days | 67 |
| 1 day | 46 |
| 60 days | 43 |
| 21 days | 41 |
| 45 days | 30 |
| 90 days | 20 |
| 28 days | 18 |
| 6 hours | 9 |
| 180 days | 9 |
| 9 days | 6 |
| 12 hours | 5 |
| 4 hours | 5 |
| 20 days | 5 |
| 15 days | 5 |
| 1 hour | 4 |
| 120 days | 4 |
| 6 days | 3 |
| 75 days | 3 |
| 11 days | 3 |
| 365 days | 2 |
| 3 hours | 1 |
| 15 hours | 1 |
| 16 hours | 1 |

### B. 311 Resolution Satisfaction Survey (`5ijn-vbdv`)

- Grouped count response: `data/raw/related/5ijn-vbdv/by_year_month.json`
- Rows with `year >= 2025` received: **275467**; expected from grouped counts: **275467**; match: **True**
- Pages: **6**; manifest: `data/raw/related/5ijn-vbdv/year_gte_2025/_manifest.json`

#### Counts by year and month (all periods in grouped response)

| year | month | count |
| --- | --- | --- |
| 2022 | 9 | 3277 |
| 2022 | 10 | 12180 |
| 2022 | 11 | 10900 |
| 2022 | 12 | 11582 |
| 2023 | 1 | 12434 |
| 2023 | 2 | 9746 |
| 2023 | 3 | 11288 |
| 2023 | 4 | 11239 |
| 2023 | 5 | 11658 |
| 2023 | 6 | 11599 |
| 2023 | 7 | 6347 |
| 2023 | 8 | 7224 |
| 2023 | 9 | 893 |
| 2023 | 10 | 9907 |
| 2023 | 11 | 9525 |
| 2023 | 12 | 10050 |
| 2024 | 1 | 11864 |
| 2024 | 2 | 8349 |
| 2024 | 3 | 11313 |
| 2024 | 4 | 10790 |
| 2024 | 5 | 10287 |
| 2024 | 6 | 14806 |
| 2024 | 7 | 12681 |
| 2024 | 8 | 11072 |
| 2024 | 9 | 11694 |
| 2024 | 10 | 12399 |
| 2024 | 11 | 12906 |
| 2024 | 12 | 13391 |
| 2025 | 1 | 14619 |
| 2025 | 2 | 11753 |
| 2025 | 3 | 14695 |
| 2025 | 4 | 13319 |
| 2025 | 5 | 15117 |
| 2025 | 6 | 13075 |
| 2025 | 7 | 13262 |
| 2025 | 8 | 13104 |
| 2025 | 9 | 13866 |
| 2025 | 10 | 13445 |
| 2025 | 11 | 11685 |
| 2025 | 12 | 11990 |
| 2026 | 1 | 13739 |
| 2026 | 2 | 15662 |
| 2026 | 3 | 14760 |
| 2026 | 4 | 14372 |
| 2026 | 5 | 15043 |
| 2026 | 6 | 10685 |
| 2026 | 7 | 10517 |
| 2026 | 8 | 15465 |
| 2026 | 9 | 5294 |

#### `overall_satisfaction` values

| overall_satisfaction | count |
| --- | --- |
| Strongly Disagree | 158258 |
| Strongly Agree | 63942 |
| Agree | 22741 |
| Disagree | 18897 |
| Neutral | 11629 |

#### `dissatisfaction_reason` values

| dissatisfaction_reason | count |
| --- | --- |
| (null) | 98543 |
| Other | 69355 |
| The Agency did not correct the issue and this Service Request should be reopened. | 57513 |
| The Agency did not correct the issue. | 35381 |
| Status updates were unhelpful, inaccurate, incomplete, and/or confusing. | 7891 |
| The Agency corrected the issue, but they took too long to respond. | 2734 |
| The Agency said I did not provide complete or accurate information, but I did. | 1526 |
| The Agency did not provide enough status updates. | 1446 |
| The Agency corrected the issue, but the work they did was unsatisfactory. | 1078 |

#### Top 20 `complaint_type` values

| complaint_type | count |
| --- | --- |
| Illegal Parking | 85346 |
| Noise - Residential | 16499 |
| Heat/Hot Water | 14440 |
| Blocked Driveway | 13297 |
| Missed Collection | 8717 |
| Abandoned Vehicle | 7341 |
| Water Maintenance | 6069 |
| Dirty Condition | 5791 |
| Noise - Street/Sidewalk | 5745 |
| Unsanitary Condition | 5740 |
| Noise | 4795 |
| Noise - Commercial | 4729 |
| Illegal Dumping | 4295 |
| Street Condition | 4045 |
| Sewer Maintenance | 4005 |
| Plumbing | 3742 |
| Encampment | 3491 |
| Damaged Tree | 3437 |
| Paint/Plaster | 3233 |
| Snow or Ice | 2972 |

Acquisition log(s): `logs/acquire_20260925T115237Z.log`

### Pull 2 Problems

- None observed.

### Pull 2 deliverables checklist

- done — SLA raw all-row count
- done — SLA full pages and manifest
- done — Survey raw year/month counts
- done — Survey year >= 2025 pages and manifest
- done — Pull 2 report section
- done — Pull 2 UTC acquisition log
