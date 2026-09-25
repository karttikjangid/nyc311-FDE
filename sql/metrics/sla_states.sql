-- Descriptive: response-target match states per agency (2024 reference, not a repair date).
SELECT sr.agency, rt.sla_state, COUNT(*) AS requests,
       ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY sr.agency), 4) AS share_of_agency
FROM service_request sr JOIN response_target rt ON rt.unique_key = sr.unique_key
GROUP BY sr.agency, rt.sla_state
ORDER BY sr.agency, requests DESC;
