# =============================================================================
# Scripted browser synthetic monitor
#
# Continuously navigates the ReliFarm dashboard, simulates farm-manager
# actions (clicking the Trigger Emergency Irrigation button), and ~25% of
# runs sends a malicious payload directly to yield-forecast that propagates
# through to core-engine and triggers an intentional 500 error path. This
# populates NR error analytics + DT charts for the demo.
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

  synthetic_script = <<-EOT
    // ReliFarm farm-manager simulation
    // Runs against the Chrome browser runtime; uses Selenium's $browser /
    // $driver globals plus in-page fetch() so the error-injection request
    // picks up the same CORS + W3C trace headers a real browser would.
    var DASHBOARD_URL      = "${local.dashboard_url}";
    var YIELD_FORECAST_URL = "${local.yield_forecast_url}";

    // ~25% of runs trigger the intentional 500 path so error analytics fill in.
    var ERROR_RUN_PROBABILITY = 0.25;
    var doErrorRun = Math.random() < ERROR_RUN_PROBABILITY;

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
      console.log("clicking emergency irrigation");
      return btn.click();
    }).then(function () {
      return $browser.sleep(3500);  // let the toast render + AJAX finish
    }).then(function () {
      if (!doErrorRun) {
        console.log("happy-path run complete");
        return;
      }
      // Edge-case: malicious payload sent in-page with fetch(). The
      // `emergency_override` field tunnels through both Lambdas and
      // triggers the 500 path in core-engine.
      console.log("error-injection run: posting emergency_override payload");
      var injectScript = ""
        + "var done = arguments[arguments.length - 1];"
        + "fetch('" + YIELD_FORECAST_URL + "', {"
        + "  method: 'POST',"
        + "  headers: { 'Content-Type': 'application/json' },"
        + "  body: JSON.stringify({"
        + "    sector_id: 'NW-A1',"
        + "    soil_moisture_pct: 18.0,"
        + "    soil_temp_c: 29.5,"
        + "    area_hectares: 42.5,"
        + "    triggered_by: 'synthetic',"
        + "    emergency_override: 'force_failure'"
        + "  })"
        + "}).then(function (r) { done(r.status); })"
        + " .catch(function (e) { done('error: ' + e.message); });";
      return $browser.executeAsyncScript(injectScript).then(function (status) {
        console.log("error-injection response: " + status);
      });
    });
  EOT
}

resource "newrelic_synthetics_script_monitor" "farm_manager" {
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
