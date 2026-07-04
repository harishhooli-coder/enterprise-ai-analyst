-- BigQuery bootstrap for Data-Answers Agent walking skeleton.
-- Replace {project} and {dataset} before running, or pass via bq query --parameter.

CREATE SCHEMA IF NOT EXISTS `{project}.{dataset}`
OPTIONS (
  location = 'US',
  description = 'Data-Answers Agent dev dataset (skeleton seed data)'
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.sales` (
  month STRING NOT NULL,
  region STRING NOT NULL,
  amount FLOAT64 NOT NULL,
  net_amount FLOAT64 NOT NULL
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.orders` (
  order_id STRING NOT NULL,
  month STRING NOT NULL,
  region STRING NOT NULL,
  order_amount FLOAT64 NOT NULL
);

CREATE TABLE IF NOT EXISTS `{project}.{dataset}.customers` (
  customer_id STRING NOT NULL,
  month STRING NOT NULL,
  region STRING NOT NULL
);
