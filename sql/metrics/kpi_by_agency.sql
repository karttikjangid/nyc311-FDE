-- Project KPI: record-answerability proxy at the as-of time, per agency.
-- Deep-dive agencies get all five checks; other agencies only the checks that need no note coding.
SELECT agency,
       COUNT(*) AS requests,
       MAX(deep) AS deep_dive,
       ROUND(AVG(result = 'ANSWERABLE'), 4)        AS answerable_share,
       ROUND(AVG(result = 'UNKNOWN'), 4)           AS unknown_share,
       ROUND(AVG(result = 'FAIL'), 4)              AS fail_share,
       ROUND(AVG(result_strict = 'ANSWERABLE'), 4) AS answerable_share_strict,
       ROUND(AVG(a1_chronology = 'FAIL'), 4)       AS a1_fail,
       ROUND(AVG(a2_status_date = 'FAIL'), 4)      AS a2_fail,
       ROUND(AVG(a3_outcome = 'FAIL'), 4)          AS a3_fail,
       ROUND(AVG(a3_outcome = 'UNKNOWN'), 4)       AS a3_unknown,
       SUM(a4_response_target <> 'NA')             AS open_requests,
       ROUND(1.0 * SUM(a4_response_target = 'PASS')    / NULLIF(SUM(a4_response_target <> 'NA'), 0), 4) AS a4_pass_of_open,
       ROUND(1.0 * SUM(a4_response_target = 'FAIL')    / NULLIF(SUM(a4_response_target <> 'NA'), 0), 4) AS a4_fail_of_open,
       ROUND(1.0 * SUM(a4_response_target = 'UNKNOWN') / NULLIF(SUM(a4_response_target <> 'NA'), 0), 4) AS a4_unknown_of_open,
       ROUND(AVG(a5_record_holder = 'FAIL'), 4)    AS a5_fail,
       ROUND(AVG(a5_record_holder = 'UNKNOWN'), 4) AS a5_unknown
FROM answerability
GROUP BY agency
ORDER BY deep_dive DESC, requests DESC;
