-- Supporting metric 3 (interaction, context only): agent-handled "Service Request Status" calls per week,
-- beside new service requests per week. Different grain and undercounted; not a per-request rate.
WITH calls AS (
  SELECT strftime('%Y-W%W', call_date) AS week, SUM(calls) AS status_calls
  FROM status_calls_daily WHERE inquiry_name = 'Service Request Status' GROUP BY week
), reqs AS (
  SELECT strftime('%Y-W%W', created_ts) AS week, COUNT(*) AS new_requests
  FROM service_request GROUP BY week
)
SELECT reqs.week, reqs.new_requests, COALESCE(calls.status_calls, 0) AS status_calls
FROM reqs LEFT JOIN calls USING (week)
ORDER BY reqs.week;
