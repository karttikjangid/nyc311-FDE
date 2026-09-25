-- Supporting metric 2: of requests not Closed at the as-of time, how many say what happens next?
SELECT co.agency,
       COUNT(*) AS open_requests,
       SUM(co.next_step IN ('agency', 'other_party', 'resident')) AS with_next_step,
       SUM(co.next_step = 'none') AS no_next_step,
       SUM(co.next_step IS NULL) AS note_missing_or_unmapped,
       ROUND(1.0 * SUM(co.next_step IN ('agency', 'other_party', 'resident')) / COUNT(*), 4) AS next_step_rate
FROM closure_outcome co
WHERE co.status <> 'Closed'
  AND co.agency IN (SELECT value FROM run_context WHERE key = 'deep_dive_agency')
GROUP BY co.agency
ORDER BY open_requests DESC;
