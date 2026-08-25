# =============================================================================
# Scripted browser synthetic monitor
#
# Continuously navigates the ReliFarm dashboard, simulates farm-manager
# actions (clicking the Trigger Emergency Irrigation button on whichever
# sector row it lands on), and on two independent random rolls:
#   - ~25% of runs sends a malicious payload directly to yield-forecast
#     (targeting the same sector that was just clicked) that propagates
#     through to core-engine and triggers an intentional 500 error path.
#   - A separate roll sends a malformed body directly to valve-scheduler,
#     triggering that Lambda's own 400 bad-request path.
# This populates NR error analytics + DT charts for the demo.
# =============================================================================

locals {
  dashboard_url = var.enable_custom_domain ? (
    "https://${var.custom_domain_name}"
    ) : (
    "https://${aws_cloudfront_distribution.dashboard.domain_name}"
  )

  # Same URL the dashboard fetches against — keeps synthetic, real-user, and
  # output traffic on a single origin so RUM and APM data line up.
  yield_forecast_url = local.use_api_custom_domain ? (
    "https://${var.api_custom_domain_name}/yield-forecast"
    ) : (
    "${aws_apigatewayv2_api.relifarm.api_endpoint}/yield-forecast"
  )

  # valve-scheduler has its own public route (aws_apigatewayv2_route.valve_scheduler_post
  # in lambdas.tf) but nothing referenced it directly until the dashboard's
  # "Missing field" demo-trigger button and this file's malformed-payload
  # branch below.
  valve_scheduler_url = local.use_api_custom_domain ? (
    "https://${var.api_custom_domain_name}/valve-schedule"
    ) : (
    "${aws_apigatewayv2_api.relifarm.api_endpoint}/valve-schedule"
  )

  synthetic_script = <<-EOT
    // ReliFarm farm-manager simulation
    // Runs against the Chrome browser runtime; uses Selenium's $browser /
    // $driver globals plus in-page fetch() so the error-injection requests
    // pick up the same CORS + W3C trace headers a real browser would.
    var DASHBOARD_URL       = "${local.dashboard_url}";
    var YIELD_FORECAST_URL  = "${local.yield_forecast_url}";
    var VALVE_SCHEDULER_URL = "${local.valve_scheduler_url}";

    // Two independent rolls so the two failure modes don't always coincide.
    var ERROR_RUN_PROBABILITY     = 0.25;
    var MALFORMED_RUN_PROBABILITY = 0.15;
    var doErrorRun     = Math.random() < ERROR_RUN_PROBABILITY;
    var doMalformedRun = Math.random() < MALFORMED_RUN_PROBABILITY;

    // Populated once the sector row is found, below.
    var relifarmBtn, relifarmSector, relifarmMoisture, relifarmTemp, relifarmArea;

    $browser.get(DASHBOARD_URL).then(function () {
      console.log("dashboard loaded: " + DASHBOARD_URL);
      return $browser.waitForAndFindElement(
        $driver.By.css("#sectorTable tbody tr"),
        15000
      );
    }).then(function () {
      // Realistic: scroll, pause, click a sector's Trigger button.
      return $browser.executeScript("window.scrollBy(0, 240)");
    }).then(function () {
      return $browser.sleep(1500);
    }).then(function () {
      return $browser.findElement(
        $driver.By.css("#sectorTable tbody tr:first-child button.action")
      );
    }).then(function (btn) {
      // Capture the row's own data before clicking, so the error-injection
      // payload below targets whichever sector this run actually landed on
      // instead of a hardcoded one. These are plain script-local vars (not
      // page globals) — $browser/$driver run in the Synthetics runtime, one
      // level outside the actual browser tab that executeAsyncScript below
      // reaches into, so the values get baked into that script's source
      // text via JSON.stringify()/Number() rather than shared through any
      // window object.
      relifarmBtn = btn;
      return Promise.all([
        btn.getAttribute("data-sector"),
        btn.getAttribute("data-moisture"),
        btn.getAttribute("data-temp"),
        btn.getAttribute("data-area"),
      ]);
    }).then(function (attrs) {
      relifarmSector   = attrs[0];
      relifarmMoisture = attrs[1];
      relifarmTemp     = attrs[2];
      relifarmArea     = attrs[3];
      console.log("clicking emergency irrigation on " + relifarmSector);
      return relifarmBtn.click();
    }).then(function () {
      return $browser.sleep(3500);  // let the toast render + AJAX finish
    }).then(function () {
      if (!doErrorRun) {
        console.log("happy-path run complete");
        return;
      }
      // Edge-case: malicious payload sent in-page with fetch(), targeting
      // the same sector just clicked above. The `emergency_override` field
      // tunnels through both Lambdas and triggers the 500 path in
      // core-engine.
      console.log("error-injection run: posting emergency_override payload");
      var injectScript = ""
        + "var done = arguments[arguments.length - 1];"
        + "fetch('" + YIELD_FORECAST_URL + "', {"
        + "  method: 'POST',"
        + "  headers: { 'Content-Type': 'application/json' },"
        + "  body: JSON.stringify({"
        + "    sector_id: " + JSON.stringify(relifarmSector) + ","
        + "    soil_moisture_pct: " + Number(relifarmMoisture) + ","
        + "    soil_temp_c: " + Number(relifarmTemp) + ","
        + "    area_hectares: " + Number(relifarmArea) + ","
        + "    triggered_by: 'synthetic',"
        + "    emergency_override: 'force_failure'"
        + "  })"
        + "}).then(function (r) { done(r.status); })"
        + " .catch(function (e) { done('error: ' + e.message); });";
      return $browser.executeAsyncScript(injectScript).then(function (status) {
        console.log("error-injection response: " + status);
      });
    }).then(function () {
      if (!doMalformedRun) {
        return;
      }
      // Independent failure mode: a non-JSON body sent straight to
      // valve-scheduler, exercising that Lambda's own 400 bad-request path
      // (rather than core-engine's 500 above).
      console.log("malformed-payload run: posting invalid JSON to valve-scheduler");
      var malformedScript = ""
        + "var done = arguments[arguments.length - 1];"
        + "fetch('" + VALVE_SCHEDULER_URL + "', {"
        + "  method: 'POST',"
        + "  headers: { 'Content-Type': 'application/json' },"
        + "  body: '{not valid json'"
        + "}).then(function (r) { done(r.status); })"
        + " .catch(function (e) { done('error: ' + e.message); });";
      return $browser.executeAsyncScript(malformedScript).then(function (status) {
        console.log("malformed-payload response: " + status);
      });
    });
  EOT
}

resource "newrelic_synthetics_script_monitor" "farm_manager" {
  count = var.enable_load_gen_synthetic ? 1 : 0

  name                                    = "${var.name_prefix}-farm-manager-journey"
  type                                    = "SCRIPT_BROWSER"
  period                                  = var.synthetic_period
  status                                  = "ENABLED"
  locations_public                        = var.synthetic_locations
  script                                  = local.synthetic_script
  enable_screenshot_on_failure_and_script = true

  runtime_type         = "CHROME_BROWSER"
  runtime_type_version = "100"
  script_language      = "JAVASCRIPT"
}
