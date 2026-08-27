# service levels across relifarm
###
# newrelic_service_level.core_engine_service_success_sl.sli_guid
# newrelic_service_level.yield_forecast_service_success_sl.sli_guid
# newrelic_service_level.valve_scheduler_service_success_sl.sli_guid
# newrelic_service_level.web_dash_browser_success_sl.sli_guid
###

# apm core-engine service success service level
resource "newrelic_service_level" "core_engine_service_success_sl" {
  guid        = data.newrelic_entity.core_engine_apm.guid
  name        = "${data.newrelic_entity.core_engine_apm.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.core_engine_apm.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.core_engine_apm.guid}' AND error.expected != true"
    }
  }

  objective {
    target = 95

    time_window {

      rolling {
        count = 7
        unit  = "DAY"
      }
    }
  }

  depends_on = [data.newrelic_entity.core_engine_apm]
}

# apm yield-forecast service success service level
resource "newrelic_service_level" "yield_forecast_service_success_sl" {
  guid        = data.newrelic_entity.yield_forecast_apm.guid
  name        = "${data.newrelic_entity.yield_forecast_apm.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.yield_forecast_apm.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.yield_forecast_apm.guid}' AND error.expected != true"
    }
  }

  objective {
    target = 95

    time_window {

      rolling {
        count = 7
        unit  = "DAY"
      }
    }
  }

  depends_on = [data.newrelic_entity.yield_forecast_apm]
}

# apm valve-scheduler service success service level
resource "newrelic_service_level" "valve_scheduler_service_success_sl" {
  guid        = data.newrelic_entity.valve_scheduler_apm.guid
  name        = "${data.newrelic_entity.valve_scheduler_apm.name} - Success"
  description = "Proportion of requests that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "Transaction"
      where = "entityGuid = '${data.newrelic_entity.valve_scheduler_apm.guid}'"
    }

    bad_events {
      from  = "TransactionError"
      where = "entityGuid = '${data.newrelic_entity.valve_scheduler_apm.guid}' AND error.expected != true"
    }
  }

  objective {
    target = 95

    time_window {

      rolling {
        count = 7
        unit  = "DAY"
      }
    }
  }

  depends_on = [data.newrelic_entity.valve_scheduler_apm]
}

# browser customer portal success service level
resource "newrelic_service_level" "web_dash_browser_success_sl" {
  guid        = data.newrelic_entity.web_dash_browser.guid
  name        = "${data.newrelic_entity.web_dash_browser.name} Browser - Success"
  description = "Proportion of page views that are served without errors."

  events {
    account_id = var.new_relic_account_id

    valid_events {
      from  = "PageView"
      where = "entityGuid = '${data.newrelic_entity.web_dash_browser.guid}'"
    }

    bad_events {
      from  = "JavaScriptError"
      where = "entityGuid = '${data.newrelic_entity.web_dash_browser.guid}' AND firstErrorInSession IS true"
    }
  }

  objective {
    target = 95

    time_window {

      rolling {
        count = 7
        unit  = "DAY"
      }
    }
  }

  depends_on = [data.newrelic_entity.web_dash_browser]
}
