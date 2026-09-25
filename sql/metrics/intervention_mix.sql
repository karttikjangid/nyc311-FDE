-- Supporting metric 1 (intervention): what the agency says it did, share of each agency's requests.
SELECT agency,
       COALESCE(action, 'UNMAPPED_OR_MISSING') AS action,
       COUNT(*) AS requests,
       ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY agency), 4) AS share_of_agency
FROM agency_action
WHERE agency IN (SELECT value FROM run_context WHERE key = 'deep_dive_agency')
GROUP BY agency, COALESCE(action, 'UNMAPPED_OR_MISSING')
ORDER BY agency, requests DESC;
