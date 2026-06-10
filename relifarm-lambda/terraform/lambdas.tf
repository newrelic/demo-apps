# =============================================================================
# Lambda packaging + IAM + API Gateway HTTP API + NR layer attachment
# =============================================================================

# ---------------------------------------------------------------------------
# NR Lambda layer freshness lookup
# Hits NR's region-specific layer index unconditionally. Used for two
# purposes:
#   1. When nr_layer_source = "auto-latest", supplies the ARN we attach.
#   2. When nr_layer_source = "pinned", drives the freshness check below so
#      stale repo pins surface loudly at plan time.
# Skipped when nr_layer_source = "local" (the user has explicitly opted out
# of cross-account / external lookups in that mode).
# ---------------------------------------------------------------------------
data "http" "nr_layer_index" {
  count = var.nr_layer_source == "local" ? 0 : 1

  url = "https://${data.aws_region.current.name}.layers.newrelic-external.com/get-layers?CompatibleRuntime=${var.lambda_runtime}&CompatibleArchitecture=x86_64"

  request_headers = {
    Accept = "application/json"
  }
}

locals {
  # Layer-name shape: NewRelicPython312, NewRelicPython313, etc. Derived from
  # var.lambda_runtime so a runtime bump doesn't desync the layer reference.
  nr_layer_runtime_suffix = replace(replace(var.lambda_runtime, "python", ""), ".", "")
  nr_layer_name           = "NewRelicPython${local.nr_layer_runtime_suffix}"
  nr_layer_account        = "451483290750"

  # Parse NR's index. try() so a malformed or unavailable response degrades
  # gracefully to nulls; the check block below treats null as "unknown".
  nr_layer_index_body     = try(jsondecode(data.http.nr_layer_index[0].response_body), null)
  nr_layer_latest_version = try(local.nr_layer_index_body.Layers[0].LatestMatchingVersion.Version, null)
  nr_layer_latest_arn     = try(local.nr_layer_index_body.Layers[0].LatestMatchingVersion.LayerVersionArn, null)

  # Active ARN — three-way switch on nr_layer_source.
  lambda_layer_arn = (
    var.nr_layer_source == "local" ? aws_lambda_layer_version.newrelic_local[0].arn :
    var.nr_layer_source == "auto-latest" ? local.nr_layer_latest_arn :
    "arn:aws:lambda:${data.aws_region.current.name}:${local.nr_layer_account}:layer:${local.nr_layer_name}:${var.new_relic_lambda_layer_version}"
  )

  # Numeric version actually in use, for the status output.
  nr_layer_version_in_use = (
    var.nr_layer_source == "local" ? aws_lambda_layer_version.newrelic_local[0].version :
    var.nr_layer_source == "auto-latest" ? local.nr_layer_latest_version :
    var.new_relic_lambda_layer_version
  )

  # Common NR env vars for both Lambdas (layer reads these on cold start).
  newrelic_lambda_env = {
    NEW_RELIC_LAMBDA_HANDLER               = "handler.lambda_handler"
    NEW_RELIC_ACCOUNT_ID                   = tostring(var.new_relic_account_id)
    NEW_RELIC_LICENSE_KEY                  = var.new_relic_license_key
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED  = "true"
    NEW_RELIC_EXTENSION_SEND_FUNCTION_LOGS = "true"
    NEW_RELIC_LAMBDA_EXTENSION_ENABLED     = "true"
    NEW_RELIC_APM_LAMBDA_MODE              = "true"

    # Demo intent: collect ~100% of spans + transactions. The Python agent
    # inside the layer uses reservoir sampling; setting these to the max
    # (10000 per harvest cycle) gives effectively-unlimited headroom for
    # this demo's volume. For true server-side 100% with zero agent-side
    # reservoir, configure NR Infinite Tracing on the account.
    NEW_RELIC_SPAN_EVENTS_MAX_SAMPLES_STORED        = "10000"
    NEW_RELIC_TRANSACTION_EVENTS_MAX_SAMPLES_STORED = "10000"
  }
}

# ---------------------------------------------------------------------------
# Local NR layer (workaround mode) — uploads a downloaded NR layer zip into
# your own account so cross-account `lambda:GetLayerVersion` is sidestepped.
# Bumping the file (filebase64sha256 changes) creates a new LayerVersion,
# which the Lambda functions automatically pick up via local.lambda_layer_arn.
# ---------------------------------------------------------------------------
resource "aws_lambda_layer_version" "newrelic_local" {
  count = var.nr_layer_source == "local" ? 1 : 0

  layer_name          = "${var.name_prefix}-newrelic-python-local"
  description         = "Local copy of ${local.nr_layer_name} — bundled to bypass cross-account lambda:GetLayerVersion SCP denials."
  filename            = "${path.module}/${var.local_nr_layer_zip_path}"
  source_code_hash    = filebase64sha256("${path.module}/${var.local_nr_layer_zip_path}")
  compatible_runtimes = [var.lambda_runtime]
}

# ---------------------------------------------------------------------------
# Freshness check — fires a loud plan-time WARNING when:
#   nr_layer_source = "pinned" AND repo's pin lags behind NR's published latest.
# Doesn't block apply (check blocks are warnings, not errors). Stays silent
# in 'auto-latest' (always current by definition) and 'local' (user has
# opted out of the external lookup).
# ---------------------------------------------------------------------------
check "nr_layer_currency" {
  assert {
    condition = (
      var.nr_layer_source != "pinned" ||
      local.nr_layer_latest_version == null ||
      var.new_relic_lambda_layer_version >= local.nr_layer_latest_version
    )
    error_message = <<-MSG

      ============================================================================
        NEW RELIC LAMBDA LAYER VERSION DRIFT
      ============================================================================
        Repo pin:      ${local.nr_layer_name}:${var.new_relic_lambda_layer_version}
        NR latest:     ${local.nr_layer_name}:${coalesce(local.nr_layer_latest_version, 0)}
        Behind by:     ${coalesce(local.nr_layer_latest_version, 0) - var.new_relic_lambda_layer_version} version(s)

        This repo is a sample app — its pinned NR layer version is not patched
        on a regular cadence, and NR has published newer revisions since this
        commit. The deployment will still work, but you'll be missing recent
        agent fixes / instrumentation updates.

        To upgrade in place, set in terraform.tfvars:
          new_relic_lambda_layer_version = ${coalesce(local.nr_layer_latest_version, 0)}

        To track NR's latest automatically, switch modes in terraform.tfvars:
          nr_layer_source = "auto-latest"
      ============================================================================
    MSG
  }
}

# ---------------------------------------------------------------------------
# Build artefacts — assemble each Lambda into a flat build dir
# (`build/<name>/`) containing handler.py + dependency wheels at the zip root,
# then archive that dir. AWS Lambda's import path is the zip root, so deps
# must live there — not under a `package/` subdir.
# ---------------------------------------------------------------------------
resource "null_resource" "package_yield_forecast" {
  triggers = {
    handler_sha  = filesha256("${path.module}/../lambdas/yield-forecast/handler.py")
    requirements = filesha256("${path.module}/../lambdas/yield-forecast/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      BUILD_DIR="${path.module}/build/yield-forecast"
      rm -rf "$BUILD_DIR"
      mkdir -p "$BUILD_DIR"
      cp ${path.module}/../lambdas/yield-forecast/handler.py "$BUILD_DIR/"
      python3 -m pip install --target "$BUILD_DIR" --quiet -r ${path.module}/../lambdas/yield-forecast/requirements.txt
    EOT
  }
}

resource "null_resource" "package_valve_scheduler" {
  triggers = {
    handler_sha  = filesha256("${path.module}/../lambdas/valve-scheduler/handler.py")
    requirements = filesha256("${path.module}/../lambdas/valve-scheduler/requirements.txt")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      BUILD_DIR="${path.module}/build/valve-scheduler"
      rm -rf "$BUILD_DIR"
      mkdir -p "$BUILD_DIR"
      cp ${path.module}/../lambdas/valve-scheduler/handler.py "$BUILD_DIR/"
      python3 -m pip install --target "$BUILD_DIR" --quiet -r ${path.module}/../lambdas/valve-scheduler/requirements.txt
    EOT
  }
}

data "archive_file" "yield_forecast_zip" {
  type        = "zip"
  source_dir  = "${path.module}/build/yield-forecast"
  output_path = "${path.module}/build/yield-forecast.zip"
  excludes    = ["*.pyc", "__pycache__"]
  depends_on  = [null_resource.package_yield_forecast]
}

data "archive_file" "valve_scheduler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/build/valve-scheduler"
  output_path = "${path.module}/build/valve-scheduler.zip"
  excludes    = ["*.pyc", "__pycache__"]
  depends_on  = [null_resource.package_valve_scheduler]
}

# ---------------------------------------------------------------------------
# IAM
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.name_prefix}-lambda-exec"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---------------------------------------------------------------------------
# Lambdas
# ---------------------------------------------------------------------------
resource "aws_lambda_function" "yield_forecast" {
  function_name    = "${var.name_prefix}-yield-forecast"
  role             = aws_iam_role.lambda_exec.arn
  filename         = data.archive_file.yield_forecast_zip.output_path
  source_code_hash = data.archive_file.yield_forecast_zip.output_base64sha256
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory_mb
  timeout          = var.lambda_timeout_seconds

  # The NR layer wraps your handler. AWS calls this; the layer then calls the
  # real handler named in NEW_RELIC_LAMBDA_HANDLER below.
  handler = "newrelic_lambda_wrapper.handler"
  layers  = [local.lambda_layer_arn]

  environment {
    variables = merge(local.newrelic_lambda_env, {
      VALVE_SCHEDULER_URL = "${aws_apigatewayv2_api.relifarm.api_endpoint}/valve-schedule"
    })
  }
}

resource "aws_lambda_function" "valve_scheduler" {
  function_name    = "${var.name_prefix}-valve-scheduler"
  role             = aws_iam_role.lambda_exec.arn
  filename         = data.archive_file.valve_scheduler_zip.output_path
  source_code_hash = data.archive_file.valve_scheduler_zip.output_base64sha256
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory_mb
  timeout          = var.lambda_timeout_seconds

  handler = "newrelic_lambda_wrapper.handler"
  layers  = [local.lambda_layer_arn]

  environment {
    variables = merge(local.newrelic_lambda_env, {
      CORE_ENGINE_URL = "https://${aws_apprunner_service.core_engine.service_url}"
    })
  }
}

# ---------------------------------------------------------------------------
# API Gateway HTTP API — single API exposing both Lambda routes with CORS
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_api" "relifarm" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type", "traceparent", "tracestate", "newrelic"]
    allow_methods = ["POST", "OPTIONS"]
    allow_origins = ["*"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.relifarm.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "yield_forecast" {
  api_id                 = aws_apigatewayv2_api.relifarm.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.yield_forecast.invoke_arn
  integration_method     = "POST"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "valve_scheduler" {
  api_id                 = aws_apigatewayv2_api.relifarm.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.valve_scheduler.invoke_arn
  integration_method     = "POST"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "yield_forecast_post" {
  api_id    = aws_apigatewayv2_api.relifarm.id
  route_key = "POST /yield-forecast"
  target    = "integrations/${aws_apigatewayv2_integration.yield_forecast.id}"
}

resource "aws_apigatewayv2_route" "valve_scheduler_post" {
  api_id    = aws_apigatewayv2_api.relifarm.id
  route_key = "POST /valve-schedule"
  target    = "integrations/${aws_apigatewayv2_integration.valve_scheduler.id}"
}

resource "aws_lambda_permission" "yield_forecast_invoke" {
  statement_id  = "AllowAPIGatewayInvokeYieldForecast"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.yield_forecast.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.relifarm.execution_arn}/*/*"
}

resource "aws_lambda_permission" "valve_scheduler_invoke" {
  statement_id  = "AllowAPIGatewayInvokeValveScheduler"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.valve_scheduler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.relifarm.execution_arn}/*/*"
}

# ---------------------------------------------------------------------------
# Optional API Gateway custom domain (gated on local.use_api_custom_domain).
# The cert + DNS records are provisioned in dns.tf; this block attaches the
# domain to the existing $default stage so /yield-forecast and /valve-schedule
# resolve under api.example.com (or whatever var.api_custom_domain_name is).
# ---------------------------------------------------------------------------
resource "aws_apigatewayv2_domain_name" "api" {
  count = local.use_api_custom_domain ? 1 : 0

  domain_name = var.api_custom_domain_name

  domain_name_configuration {
    certificate_arn = local.api_acm_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  count = local.use_api_custom_domain ? 1 : 0

  api_id      = aws_apigatewayv2_api.relifarm.id
  domain_name = aws_apigatewayv2_domain_name.api[0].id
  stage       = aws_apigatewayv2_stage.default.id
}
