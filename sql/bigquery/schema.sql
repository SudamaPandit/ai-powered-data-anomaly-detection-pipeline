CREATE SCHEMA IF NOT EXISTS `PROJECT_ID.data_observability`
OPTIONS (location = 'US');

CREATE TABLE IF NOT EXISTS `PROJECT_ID.data_observability.detection_runs` (
  run_id STRING NOT NULL,
  dataset STRING NOT NULL,
  batch_id STRING NOT NULL,
  observed_at TIMESTAMP NOT NULL,
  row_count INT64 NOT NULL,
  duplicate_rate FLOAT64,
  null_member_rate FLOAT64,
  invalid_amount_rate FLOAT64,
  invalid_status_rate FLOAT64,
  invalid_timestamp_rate FLOAT64,
  mean_amount FLOAT64,
  p95_amount FLOAT64,
  freshness_hours FLOAT64,
  model_score FLOAT64 NOT NULL,
  model_anomaly BOOL NOT NULL,
  is_anomaly BOOL NOT NULL,
  final_severity STRING NOT NULL,
  metrics JSON
)
PARTITION BY DATE(observed_at)
CLUSTER BY dataset, final_severity;

CREATE TABLE IF NOT EXISTS `PROJECT_ID.data_observability.rule_findings` (
  run_id STRING NOT NULL,
  rule_id STRING NOT NULL,
  severity STRING NOT NULL,
  metric STRING NOT NULL,
  observed FLOAT64 NOT NULL,
  threshold FLOAT64 NOT NULL,
  message STRING NOT NULL
)
CLUSTER BY severity, rule_id;

