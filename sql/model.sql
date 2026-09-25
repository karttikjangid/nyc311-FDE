-- Workflow views: intervention (agency_action) and outcome (closure_outcome) per request,
-- and the record-answerability checks A1-A5 (docs/00_plan.md section 5).

CREATE VIEW agency_action AS
SELECT sr.unique_key, sr.agency, sr.complaint_type, sr.status,
       cn.action, cn.certainty, cn.mapping_version
FROM service_request sr LEFT JOIN closing_note cn ON cn.note_hash = sr.note_hash;

CREATE VIEW closure_outcome AS
SELECT sr.unique_key, sr.agency, sr.complaint_type, sr.status,
       cn.violation_finding, cn.fix_evidence, cn.next_step, cn.redirects_elsewhere, cn.certainty
FROM service_request sr LEFT JOIN closing_note cn ON cn.note_hash = sr.note_hash;

CREATE TABLE answerability AS
WITH base AS (
  SELECT sr.unique_key, sr.agency, sr.complaint_type, sr.status,
         sr.agency IN (SELECT value FROM run_context WHERE key = 'deep_dive_agency') AS deep,
         sr.flag_closed_before_created, sr.flag_action_before_created, sr.flag_status_date_conflict,
         sr.flag_note_missing, cn.note_hash AS mapped, cn.certainty, cn.next_step, cn.redirects_elsewhere,
         rt.sla_state
  FROM service_request sr
  LEFT JOIN closing_note cn ON cn.note_hash = sr.note_hash
  LEFT JOIN response_target rt ON rt.unique_key = sr.unique_key
), checks AS (
  SELECT unique_key, agency, complaint_type, status, deep,
    CASE WHEN flag_closed_before_created = 1 OR flag_action_before_created = 1 THEN 'FAIL' ELSE 'PASS' END AS a1_chronology,
    CASE WHEN flag_status_date_conflict = 1 THEN 'FAIL' ELSE 'PASS' END AS a2_status_date,
    CASE WHEN NOT deep THEN 'NOT_CODED'
         WHEN flag_note_missing = 1 THEN 'FAIL'
         WHEN mapped IS NULL OR certainty = 'low' THEN 'UNKNOWN'
         WHEN status = 'Closed' THEN 'PASS'
         WHEN next_step IN ('agency', 'other_party', 'resident') THEN 'PASS'
         ELSE 'FAIL' END AS a3_outcome,
    CASE WHEN NOT deep THEN 'NOT_CODED'
         WHEN flag_note_missing = 1 THEN 'FAIL'
         WHEN mapped IS NULL OR certainty IN ('low', 'medium') THEN 'UNKNOWN'
         WHEN status = 'Closed' THEN 'PASS'
         WHEN next_step IN ('agency', 'other_party', 'resident') THEN 'PASS'
         ELSE 'FAIL' END AS a3_outcome_strict,
    CASE WHEN status = 'Closed' THEN 'NA'
         WHEN sla_state = 'MATCHED' THEN 'PASS'
         WHEN sla_state = 'NOT_MANAGED_BY_311' THEN 'FAIL'
         ELSE 'UNKNOWN' END AS a4_response_target,
    CASE WHEN NOT deep THEN 'NOT_CODED'
         WHEN mapped IS NULL THEN 'UNKNOWN'
         WHEN redirects_elsewhere = 'yes' THEN 'FAIL'
         ELSE 'PASS' END AS a5_record_holder
  FROM base
)
SELECT *,
  -- First failing check in root-cause order: data integrity, then record holder, then note, then target.
  CASE WHEN NOT deep THEN NULL
       WHEN a1_chronology = 'FAIL' THEN 'A1'
       WHEN a2_status_date = 'FAIL' THEN 'A2'
       WHEN a5_record_holder = 'FAIL' THEN 'A5'
       WHEN a3_outcome IN ('FAIL', 'UNKNOWN') THEN 'A3'
       WHEN a5_record_holder = 'UNKNOWN' THEN 'A5'
       WHEN a4_response_target IN ('FAIL', 'UNKNOWN') THEN 'A4'
  END AS primary_blocker,
  CASE WHEN NOT deep THEN NULL
       WHEN a1_chronology = 'FAIL' THEN 'A1'
       WHEN a2_status_date = 'FAIL' THEN 'A2'
       WHEN a5_record_holder = 'FAIL' THEN 'A5'
       WHEN a3_outcome_strict IN ('FAIL', 'UNKNOWN') THEN 'A3'
       WHEN a5_record_holder = 'UNKNOWN' THEN 'A5'
       WHEN a4_response_target IN ('FAIL', 'UNKNOWN') THEN 'A4'
  END AS primary_blocker_strict,
  CASE WHEN NOT deep THEN 'NOT_ASSESSED'
       WHEN 'FAIL' IN (a1_chronology, a2_status_date, a3_outcome, a4_response_target, a5_record_holder) THEN 'FAIL'
       WHEN 'UNKNOWN' IN (a3_outcome, a4_response_target, a5_record_holder) THEN 'UNKNOWN'
       ELSE 'ANSWERABLE' END AS result,
  CASE WHEN NOT deep THEN 'NOT_ASSESSED'
       WHEN 'FAIL' IN (a1_chronology, a2_status_date, a3_outcome_strict, a4_response_target, a5_record_holder) THEN 'FAIL'
       WHEN 'UNKNOWN' IN (a3_outcome_strict, a4_response_target, a5_record_holder) THEN 'UNKNOWN'
       ELSE 'ANSWERABLE' END AS result_strict
FROM checks;

CREATE UNIQUE INDEX ix_ans ON answerability(unique_key);
