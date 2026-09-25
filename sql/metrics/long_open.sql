-- Descriptive: share of requests open longer than N days at the as-of time T.
-- Closed with valid dates: closed - created. Not Closed: censored at T (T - created).
-- Closed with missing or impossible closed date: unknown, kept in the denominator.
WITH t AS (SELECT value AS as_of FROM run_context WHERE key = 'as_of_local'),
n AS (SELECT CAST(value AS REAL) AS days FROM run_context WHERE key = 'long_open_days'),
d AS (
  SELECT sr.agency,
         CASE WHEN sr.status = 'Closed' AND sr.closed_ts IS NOT NULL AND sr.closed_ts >= sr.created_ts
                THEN julianday(sr.closed_ts) - julianday(sr.created_ts)
              WHEN sr.status <> 'Closed'
                THEN julianday((SELECT as_of FROM t)) - julianday(sr.created_ts)
         END AS open_days
  FROM service_request sr
)
SELECT agency, COUNT(*) AS requests,
       ROUND(AVG(open_days > (SELECT days FROM n)), 4) AS share_open_longer_than_n_days_known,
       ROUND(1.0 * SUM(open_days > (SELECT days FROM n)) / COUNT(*), 4) AS share_open_longer_than_n_days,
       ROUND(AVG(open_days IS NULL), 4) AS share_unknown
FROM d GROUP BY agency ORDER BY requests DESC;
