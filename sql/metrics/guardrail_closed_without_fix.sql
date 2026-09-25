-- Guardrail: Closed requests whose note gives no evidence the condition was corrected.
-- This is what an assistant would get wrong if it read status = Closed as "fixed".
SELECT agency,
       COUNT(*) AS closed_requests,
       SUM(fix_evidence IS NULL) AS unmapped_or_missing_note,
       SUM(fix_evidence = 'yes') AS fix_yes,
       SUM(fix_evidence = 'yes' AND certainty = 'high') AS fix_yes_high_certainty,
       ROUND(1.0 * SUM(fix_evidence IS NOT NULL AND fix_evidence <> 'yes') / NULLIF(SUM(fix_evidence IS NOT NULL), 0), 4) AS closed_without_fix_evidence,
       ROUND(1.0 * SUM(fix_evidence IS NOT NULL AND NOT (fix_evidence = 'yes' AND certainty = 'high')) / NULLIF(SUM(fix_evidence IS NOT NULL), 0), 4) AS closed_without_fix_evidence_strict
FROM closure_outcome
WHERE status = 'Closed'
  AND agency IN (SELECT value FROM run_context WHERE key = 'deep_dive_agency')
GROUP BY agency
ORDER BY closed_requests DESC;
