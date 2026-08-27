# tags applied across all New Relic entities in this module

locals {
  # Three different kinds of "might not have a value" here - each needs its
  # own handling, or the whole list's length becomes unknown at plan time
  # and breaks count planning (Error: Invalid count argument).
  #
  # 1. ignore_not_found data sources (ignore_not_found = true in
  #    nr_entities.tf) can resolve to a concrete, KNOWN null at plan time if
  #    New Relic hasn't discovered the entity yet - safe to filter with
  #    `if guid != null`.
  relifarm_data_source_guids = [for guid in [
    data.newrelic_entity.core_engine_apm.guid,
    data.newrelic_entity.yield_forecast_apm.guid,
    data.newrelic_entity.valve_scheduler_apm.guid,
    data.newrelic_entity.yield_forecast_lambda.guid,
    data.newrelic_entity.valve_scheduler_lambda.guid,
    data.newrelic_entity.web_dash_browser.guid,
  ] : guid if guid != null]

  # 2. Resources created unconditionally (no count/for_each) - on first
  #    create their guid/entity_guid is simply UNKNOWN until apply, never
  #    null. Unknown values are fine as plain list elements; they only
  #    break planning when tested against `!= null` in a filter like above.
  relifarm_always_created_guids = [
    newrelic_workload.relifarm_workload.guid,
    newrelic_nrql_alert_condition.relifarm_browser_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_synthetic_failing.entity_guid,
    newrelic_nrql_alert_condition.relifarm_apm_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_lambda_low_throughput.entity_guid,
    newrelic_nrql_alert_condition.relifarm_service_level_health.entity_guid,
  ]

  # 3. Resources gated by their own count (synthetic monitor, service
  #    levels) - same "unknown on first create" problem as #2, but the
  #    count itself can also be 0. Branch on the same KNOWN condition that
  #    drives each resource's count (never on the resource's own
  #    unknown-until-apply attribute), so inclusion is decided by a value
  #    Terraform can actually evaluate at plan time.
  relifarm_conditionally_created_guids = concat(
    var.enable_load_gen_synthetic ? [newrelic_synthetics_script_monitor.farm_manager[0].guid] : [],
    data.newrelic_entity.core_engine_apm.guid != null ? [newrelic_service_level.core_engine_service_success_sl[0].sli_guid] : [],
    data.newrelic_entity.yield_forecast_apm.guid != null ? [newrelic_service_level.yield_forecast_service_success_sl[0].sli_guid] : [],
    data.newrelic_entity.valve_scheduler_apm.guid != null ? [newrelic_service_level.valve_scheduler_service_success_sl[0].sli_guid] : [],
    data.newrelic_entity.web_dash_browser.guid != null ? [newrelic_service_level.web_dash_browser_success_sl[0].sli_guid] : [],
  )

  relifarm_entity_list = concat(
    local.relifarm_data_source_guids,
    local.relifarm_always_created_guids,
    local.relifarm_conditionally_created_guids,
  )
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
