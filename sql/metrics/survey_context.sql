-- Context only: survey responses begun April-September 2026, by agency. Self-selected respondents.
SELECT agency,
       SUM(responses) AS responses,
       ROUND(1.0 * SUM(disagree) / SUM(responses), 4) AS disagree_share,
       ROUND(1.0 * SUM(reason_not_corrected) / SUM(responses), 4) AS reason_not_corrected_share,
       ROUND(1.0 * SUM(reason_status_updates) / SUM(responses), 4) AS reason_status_updates_share
FROM survey_stratum
WHERE year = 2026 AND month BETWEEN 4 AND 9
GROUP BY agency
HAVING SUM(responses) >= 100
ORDER BY responses DESC;
