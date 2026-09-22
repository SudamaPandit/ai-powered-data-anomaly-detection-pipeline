SELECT
  DATE(observed_at) AS detection_date,
  dataset,
  final_severity,
  COUNT(*) AS run_count,
  COUNTIF(is_anomaly) AS anomaly_count,
  ROUND(100 * SAFE_DIVIDE(COUNTIF(is_anomaly), COUNT(*)), 2) AS anomaly_rate_pct,
  APPROX_QUANTILES(model_score, 100)[OFFSET(95)] AS p95_model_score
FROM `PROJECT_ID.data_observability.detection_runs`
WHERE observed_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY detection_date, dataset, final_severity
ORDER BY detection_date DESC, final_severity DESC;
