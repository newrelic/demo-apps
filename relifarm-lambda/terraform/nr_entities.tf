###
# data.newrelic_entity.core_engine_apm.guid
# data.newrelic_entity.yield_forecast_apm.guid
# data.newrelic_entity.valve_scheduler_apm.guid
# data.newrelic_entity.web_dash_browser.guid
# data.newrelic_entity.yield_forecast_lambda.guid
# data.newrelic_entity.valve_scheduler_lambda.guid
###

### APM APPLICATIONS ###
# core-engine reports as classic APM via the Python agent (core-engine/app/main.py,
# core-engine/newrelic.ini). yield-forecast and valve-scheduler ALSO show up
# here, in addition to their AWS Lambda entities below - NEW_RELIC_APM_LAMBDA_MODE
# = "true" (lambdas.tf) makes the agent report each Lambda as an
# APM/APPLICATION entity too, same display name, separate GUID.
data "newrelic_entity" "core_engine_apm" {
  name             = "ReliFarm (${local.environment_display}) - Core Engine"
  domain           = "APM"
  type             = "APPLICATION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

data "newrelic_entity" "yield_forecast_apm" {
  name             = "ReliFarm (${local.environment_display}) - Yield Forecast"
  domain           = "APM"
  type             = "APPLICATION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

data "newrelic_entity" "valve_scheduler_apm" {
  name             = "ReliFarm (${local.environment_display}) - Valve Scheduler"
  domain           = "APM"
  type             = "APPLICATION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### BROWSER APPLICATION ###
data "newrelic_entity" "web_dash_browser" {
  name             = "ReliFarm (${local.environment_display}) - Web Dash"
  domain           = "BROWSER"
  type             = "APPLICATION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

### AWS LAMBDA FUNCTIONS ###
# Separate from the APM entities above - this is the Lambda-monitoring
# entity (Serverless page). Its name is the actual AWS function name
# (matches aws_lambda_function.*.function_name in lambdas.tf), not the
# branded NEW_RELIC_APP_NAME - AWS Lambda entities are synthesized from the
# function's own AWS identity, not the agent-reported app name.
data "newrelic_entity" "yield_forecast_lambda" {
  name             = "${var.name_prefix}-yield-forecast"
  domain           = "INFRA"
  type             = "AWSLAMBDAFUNCTION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}

data "newrelic_entity" "valve_scheduler_lambda" {
  name             = "${var.name_prefix}-valve-scheduler"
  domain           = "INFRA"
  type             = "AWSLAMBDAFUNCTION"
  account_id       = var.new_relic_account_id
  ignore_not_found = true
}
