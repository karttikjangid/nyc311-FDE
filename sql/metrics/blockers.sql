-- Why requests are not answerable: first failing check per request (root-cause order A1, A2, A5, A3, A4).
SELECT agency, primary_blocker, COUNT(*) AS requests,
       ROUND(1.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY agency), 4) AS share_of_agency_non_answerable
FROM answerability
WHERE deep = 1 AND result <> 'ANSWERABLE'
GROUP BY agency, primary_blocker
ORDER BY agency, requests DESC;
