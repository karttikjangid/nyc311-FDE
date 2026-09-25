-- KPI by complaint type inside the deep-dive agencies (types with at least 500 requests),
-- with the most common first-failing check (strict reading) and a proposed decision.
-- Decision rule (our proposal; owner to confirm: 311/OTI): uses the STRICT reading, to stay conservative.
-- decision_if_loose_reading shows how much the call depends on how the notes are read.
--   strict answerable >= 90%  -> candidate for a measurement pilot
--   60% to 90%                -> fix the named blocker first
--   below 60%                 -> hold
WITH t AS (
  SELECT agency, complaint_type, COUNT(*) AS requests,
         ROUND(AVG(result = 'ANSWERABLE'), 4) AS answerable_share,
         ROUND(AVG(result = 'UNKNOWN'), 4)    AS unknown_share,
         ROUND(AVG(result = 'FAIL'), 4)       AS fail_share,
         ROUND(AVG(result_strict = 'ANSWERABLE'), 4) AS answerable_share_strict
  FROM answerability WHERE deep = 1
  GROUP BY agency, complaint_type HAVING COUNT(*) >= 500
), b AS (
  SELECT agency, complaint_type, primary_blocker_strict AS primary_blocker, COUNT(*) AS n,
         ROW_NUMBER() OVER (PARTITION BY agency, complaint_type ORDER BY COUNT(*) DESC, primary_blocker_strict) AS rk
  FROM answerability WHERE deep = 1 AND result_strict <> 'ANSWERABLE'
  GROUP BY agency, complaint_type, primary_blocker_strict
)
SELECT t.*,
       b.primary_blocker AS main_blocker,
       ROUND(1.0 * COALESCE(b.n, 0) / t.requests, 4) AS main_blocker_share,
       CASE WHEN t.answerable_share_strict >= 0.90 THEN 'candidate for measurement pilot'
            WHEN t.answerable_share_strict >= 0.60 THEN 'fix blocker first'
            ELSE 'hold' END AS proposed_decision,
       CASE WHEN t.answerable_share >= 0.90 THEN 'candidate for measurement pilot'
            WHEN t.answerable_share >= 0.60 THEN 'fix blocker first'
            ELSE 'hold' END AS decision_if_loose_reading
FROM t LEFT JOIN b ON b.agency = t.agency AND b.complaint_type = t.complaint_type AND b.rk = 1
ORDER BY t.agency, t.requests DESC;
