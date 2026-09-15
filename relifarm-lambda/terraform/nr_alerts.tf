# alert policies, destinations, channels, and conditions
###
# newrelic_notification_channel.staging_slack_relifarm_channel.id
# newrelic_workflow.relifarm_slack_workflow.id
# newrelic_alert_policy.relifarm_policy.id
# newrelic_nrql_alert_condition.relifarm_browser_low_throughput.entity_guid
# newrelic_nrql_alert_condition.relifarm_synthetic_failing.entity_guid
# newrelic_nrql_alert_condition.relifarm_apm_low_throughput.entity_guid
# newrelic_nrql_alert_condition.relifarm_lambda_low_throughput.entity_guid
# newrelic_nrql_alert_condition.relifarm_service_level_health.entity_guid
###

locals {
  # web_dash_browser and the three *_apm entities (nr_entities.tf) use
  # ignore_not_found = true - on a cold environment their guid resolves to a
  # KNOWN null at plan time. Interpolating a null into a NRQL heredoc string
  # is a hard Terraform error ("Invalid template interpolation value"),
  # unlike the list/count contexts elsewhere in this repo
  # (nr_service_levels.tf, nr_entity_tags.tf) where the same null is handled
  # by gating a resource's own count.
  #
  # These two alert conditions are NOT count-gated: their entity_guid is
  # already referenced unconditionally in nr_entity_tags.tf's
  # relifarm_always_created_guids bucket (that's the alert condition's own,
  # always-computed entity_guid - a different attribute from the
  # data-source guid used inside the query body below). Gating count here
  # would force moving those two entries into the conditional bucket for no
  # real benefit, since the resource itself is always valid to create.
  # Instead, coalesce the guid used inside the query string to a placeholder
  # that can never match a real NR entity GUID - same shape as the
  # coalesce() used in lambdas.tf for local.nr_layer_latest_version.
  nr_entity_guid_placeholder = "guid-not-yet-discovered"

  relifarm_web_dash_browser_guid    = coalesce(data.newrelic_entity.web_dash_browser.guid, local.nr_entity_guid_placeholder)
  relifarm_core_engine_apm_guid     = coalesce(data.newrelic_entity.core_engine_apm.guid, local.nr_entity_guid_placeholder)
  relifarm_valve_scheduler_apm_guid = coalesce(data.newrelic_entity.valve_scheduler_apm.guid, local.nr_entity_guid_placeholder)
  relifarm_yield_forecast_apm_guid  = coalesce(data.newrelic_entity.yield_forecast_apm.guid, local.nr_entity_guid_placeholder)
}

# Staging Slack Notification Channel
resource "newrelic_notification_channel" "staging_slack_relifarm_channel" {
  account_id     = var.new_relic_account_id
  name           = "staging_slack_relifarm_channel"
  type           = "SLACK"
  destination_id = var.slack_destination_id
  product        = "IINT"

  property {
    key           = "channelId"
    value         = "C0BT6H3E82J"
    display_value = "help-relifarm-engineering"
  }
}

# Slack Workflow
resource "newrelic_workflow" "relifarm_slack_workflow" {
  account_id            = var.new_relic_account_id
  name                  = "relifarm_slack_workflow"
  enabled               = true
  muting_rules_handling = "DONT_NOTIFY_FULLY_MUTED_ISSUES"

  issues_filter {
    name = "policy_filter"
    type = "FILTER"

    predicate {
      attribute = "labels.policyIds"
      operator  = "EXACTLY_MATCHES"
      values = [
        newrelic_alert_policy.relifarm_policy.id
      ]
    }
  }

  destination {
    channel_id              = newrelic_notification_channel.staging_slack_relifarm_channel.id
    notification_triggers   = ["ACKNOWLEDGED", "ACTIVATED", "CLOSED", "INVESTIGATING"]
    update_original_message = true
  }
}

# Alert Policy
resource "newrelic_alert_policy" "relifarm_policy" {
  name                = "ReliFarm (${local.environment_display}) Policy"
  incident_preference = "PER_CONDITION_AND_TARGET"
  account_id          = var.new_relic_account_id
}

# Browser Health Alert
resource "newrelic_nrql_alert_condition" "relifarm_browser_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.relifarm_policy.id
  type                         = "static"
  name                         = "ReliFarm - Browser Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM PageView SELECT
      count(*)
    FACET appName AS 'entityName'
    WHERE entityGuid = '${local.relifarm_web_dash_browser_guid}'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Browser Low Throughput | {{ entity_name }}"
}

# APM Health Alert
resource "newrelic_nrql_alert_condition" "relifarm_apm_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.relifarm_policy.id
  type                         = "static"
  name                         = "ReliFarm - APM Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Metric SELECT
      count(apm.service.transaction.duration)
    FACET entity.name
    WHERE entity.guid IN ('${local.relifarm_core_engine_apm_guid}','${local.relifarm_valve_scheduler_apm_guid}','${local.relifarm_yield_forecast_apm_guid}')
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "APM Low Throughput | {{ entity_name }}"
}

# Lambda Health Alert
resource "newrelic_nrql_alert_condition" "relifarm_lambda_low_throughput" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.relifarm_policy.id
  type                         = "static"
  name                         = "ReliFarm - Lambda Low Throughput"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM ServerlessSample SELECT
      rate(sum(provider.invocations.Sum), 1 MINUTE)
    FACET entityName
    WHERE label.team = 'ReliFarm Engineering'
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 360
    threshold_occurrences = "all"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Lambda Low Throughput | {{ entity_name }}"
}

# Service Level Health Alert
resource "newrelic_nrql_alert_condition" "relifarm_service_level_health" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.relifarm_policy.id
  type                         = "static"
  name                         = "ReliFarm - Service Level Health"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM Entity SELECT
      count(*)
    FACET name AS 'entityName'
    WHERE type = 'EXT-SERVICE_LEVEL'
    AND id IN ('${join("','", concat(newrelic_service_level.core_engine_service_success_sl[*].sli_guid, newrelic_service_level.yield_forecast_service_success_sl[*].sli_guid, newrelic_service_level.valve_scheduler_service_success_sl[*].sli_guid, newrelic_service_level.web_dash_browser_success_sl[*].sli_guid))}')
    EOT
    )

  }

  critical {
    operator              = "below"
    threshold             = 0
    threshold_duration    = 86400
    threshold_occurrences = "all"
  }
  fill_option        = "last_value"
  aggregation_window = 21600
  aggregation_method = "event_timer"
  aggregation_timer  = 60
  title_template     = "Service Level Health | {{ entity_name }}"
}

# Synthetics Health Alert
resource "newrelic_nrql_alert_condition" "relifarm_synthetic_failing" {
  account_id                   = var.new_relic_account_id
  policy_id                    = newrelic_alert_policy.relifarm_policy.id
  type                         = "static"
  name                         = "ReliFarm - Synthetic Check Failing"
  enabled                      = true
  violation_time_limit_seconds = 10800
  nrql {

    query = trimspace(<<-EOT
    FROM SyntheticCheck SELECT
      percentage(count(*), WHERE result = 'FAILED')
    FACET locationLabel, monitorName AS 'entityName'
    WHERE NOT isMuted
    AND tags.team = 'ReliFarm Engineering'
    EOT
    )

  }

  critical {
    operator              = "above"
    threshold             = 0
    threshold_duration    = 60
    threshold_occurrences = "at_least_once"
  }
  fill_option        = "none"
  aggregation_window = 60
  aggregation_method = "event_flow"
  aggregation_delay  = 60
  evaluation_delay   = 120
  title_template     = "Synthetic Check Failing | {{ entity_name }}"
}
