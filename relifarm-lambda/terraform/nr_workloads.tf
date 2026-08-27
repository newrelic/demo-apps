# workloads for teams by default
###
# newrelic_workload.relifarm_workload.guid
###

resource "newrelic_workload" "relifarm_workload" {
  name       = "ReliFarm Engineering Components"
  account_id = var.new_relic_account_id

  entity_search_query {
    query = "tags.nr.team = 'ReliFarm Engineering'"
  }
}
