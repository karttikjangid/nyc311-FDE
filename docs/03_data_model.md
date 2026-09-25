# Workflow and data model

The raw sources are organised by system. The model reorganises them around one request's journey (Class 7).

PNG copies of the three diagrams: `img/workflow.png`, `img/data_model.png`, `img/pipeline.png`.

## 1. The request journey (interaction, intervention, outcome)

```mermaid
flowchart LR
    R([Resident]) -->|reports| SR[Service request created<br/>created_date, channel]
    SR -->|311 routes| AG[Agency assigned<br/>agency, complaint_type]
    AG -->|agency acts| ACT[Agency action<br/>inspected / no access / violation / referred / repaired]
    ACT --> ST[Status + closed_date<br/>last action only]
    ST --> OUT{{Outcome in the note<br/>fix evidence: yes / partial / no / unknown}}
    R -.->|calls 311: 'Service Request Status'<br/>NO request key| CALL[Status call]
    R -.->|answers survey<br/>NO request key| SURV[Survey response]
    SR -.->|duplicate of ...<br/>original key NOT given| DUP[Original request]
    ST -.->|DOT: 'status is on DOT's website'| EXT[(Agency system<br/>not published)]
    SLA[(SLA table 2024<br/>time to address)] -.->|text match only| AG
```

Solid lines are links we can join on. Dashed lines are links that exist in the real world but have no key in the data.

| Class 7 concept | In this project | Table |
|---|---|---|
| Entity | service request | `service_request` |
| Events / states | created, last action, closed, due | `request_event` |
| Interaction | resident reports (channel); status calls; survey answers | `service_request.open_data_channel_type`, `status_calls_daily`, `survey_stratum` |
| Intervention | what the agency says it did | `agency_action` (view) from `closing_note.action` |
| Outcome | finding, fix evidence, next step | `closure_outcome` (view) |
| Commitment | published response target | `response_target`, `sla_rule` |
| KPI grain | the five record checks per request | `answerability` |

## 2. Tables

```mermaid
erDiagram
    service_request ||--o{ request_event : "has"
    service_request }o--o| closing_note : "note_hash"
    service_request ||--|| response_target : "unique_key"
    service_request ||--|| answerability : "unique_key"
    sla_rule ||..o{ response_target : "text match (agency, problem, detail)"
    service_request {
        text unique_key PK
        text agency
        text complaint_type
        text descriptor
        text status
        text created_ts
        text closed_ts
        text last_action_ts
        text note_hash FK
        int flag_closed_before_created
        int flag_status_date_conflict
    }
    request_event {
        text unique_key FK
        text event_type
        text event_ts
        text source_field
    }
    closing_note {
        text note_hash PK
        text action
        text violation_finding
        text fix_evidence
        text next_step
        text redirects_elsewhere
        text certainty
        text mapping_version
    }
    response_target {
        text unique_key PK
        text sla_state
        real sla_hours
    }
    answerability {
        text unique_key PK
        text a1_chronology
        text a2_status_date
        text a3_outcome
        text a4_response_target
        text a5_record_holder
        text result
        text result_strict
        text primary_blocker
    }
    status_calls_daily {
        text call_date
        text inquiry_name
        int calls
    }
    survey_stratum {
        text agency
        text complaint_type_norm
        int year
        int month
        int responses
        int disagree
    }
```

`status_calls_daily` and `survey_stratum` have no relationship lines on purpose: nothing in the data connects them to a request.

## 3. Pipeline

```mermaid
flowchart LR
    API[(NYC Open Data API)] -->|keyset pages + counts| RAW[Raw snapshot<br/>gz pages + SHA-256 manifest]
    RAW --> V1{Structural checks<br/>R01-R03}
    V1 -->|FAIL| STOP[Not published<br/>logs/failed_run_*.json]
    V1 --> CL[Clean<br/>types + flags, no silent fixes]
    CL --> V2{Contract R04-R25}
    V2 -->|blocking FAIL| STOP
    V2 --> M[SQLite model<br/>sql/model.sql]
    M --> V3{R26 reconcile}
    V3 -->|FAIL| STOP
    V3 --> MET[Metrics<br/>sql/metrics/*.sql]
    MET --> PUB[output/run_date=...<br/>atomic swap]
```

## 4. The five checks behind the KPI

| Check | PASS when | FAIL when | UNKNOWN when |
|---|---|---|---|
| A1 chronology | nothing dated before creation (00:00 same-day stamps excepted) | closed or updated before created | never |
| A2 status/date | Closed has a closed date; others do not | they disagree | never |
| A3 note readable | closed: the note says what happened; open: the note says who acts next | no note, or open with no next step | note not coded, or low certainty (strict: medium too) |
| A4 response target | open request has a MATCHED target (closed: not applicable) | "SLA Not Managed by 311" | AMBIGUOUS or UNMATCHED |
| A5 record holder | note does not send the resident elsewhere | status is only in another system | note not coded |

A request is **answerable** only if every check passes. `primary_blocker` is the first failing check in root-cause order: A1, A2, A5, A3, A4.
