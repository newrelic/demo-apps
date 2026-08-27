# tags applied across all New Relic entities in this module

locals {
  # ignore_not_found data sources in nr_entities.tf can resolve to a
  # concrete null at plan time if New Relic hasn't discovered the entity
  # yet - filter those out, or the whole list's length becomes unknown and
  # breaks count planning.
  relifarm_entity_list = [for guid in [
    data.newrelic_entity.core_engine_apm.guid,
    data.newrelic_entity.yield_forecast_apm.guid,
    data.newrelic_entity.valve_scheduler_apm.guid,
    data.newrelic_entity.yield_forecast_lambda.guid,
    data.newrelic_entity.valve_scheduler_lambda.guid,
    data.newrelic_entity.web_dash_browser.guid,
    one(newrelic_synthetics_script_monitor.farm_manager[*].guid),
    one(newrelic_service_level.core_engine_service_success_sl[*].sli_guid),
    one(newrelic_service_level.yield_forecast_service_success_sl[*].sli_guid),
    one(newrelic_service_level.valve_scheduler_service_success_sl[*].sli_guid),
    one(newrelic_service_level.web_dash_browser_success_sl[*].sli_guid),
    newrelic_workload.relifarm_workload.guid,
    newrelic_nrql_alert_condition.relifarm_browser_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_synthetic_failing.entity_guid,
    newrelic_nrql_alert_condition.relifarm_apm_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_lambda_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_service_level_health.entity_guid,
  ] : guid if guid != null]
}

resource "newrelic_entity_tags" "relifarm_tags" {
  count = length(local.relifarm_entity_list)
  guid  = local.relifarm_entity_list[count.index]

  tag {
    key    = "team"
    values = ["ReliFarm Engineering"]
  }
  tag {
    key    = "deploymentTier"
    values = [var.environment]
  }
  tag {
    key    = "heroChannel"
    values = ["help-relifarm-engineering"]
  }
  tag {
    key    = "githubRepo"
    values = ["https://github.com/newrelic/demo-apps/tree/main/relifarm-lambda"]
  }
  tag {
    key    = "appStack"
    values = ["relifarm"]
  }
  tag {
    key    = "managedBy"
    values = ["terraform"]
  }

  depends_on = [local.relifarm_entity_list]
}
