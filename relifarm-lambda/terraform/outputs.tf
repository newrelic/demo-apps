output "api_base_url" {
  description = "Base URL of the API Gateway exposing both Lambdas."
  value = local.use_api_custom_domain ? (
    "https://${var.api_custom_domain_name}"
    ) : (
    aws_apigatewayv2_api.relifarm.api_endpoint
  )
}

output "yield_forecast_url" {
  description = "Public endpoint of the yield-forecast Lambda."
  value       = local.yield_forecast_url
}

output "valve_scheduler_url" {
  description = "Public endpoint of the valve-scheduler Lambda."
  value = local.use_api_custom_domain ? (
    "https://${var.api_custom_domain_name}/valve-schedule"
    ) : (
    "${aws_apigatewayv2_api.relifarm.api_endpoint}/valve-schedule"
  )
}

output "dashboard_url" {
  description = "Public URL of the ReliFarm dashboard."
  value = var.enable_custom_domain ? (
    "https://${var.custom_domain_name}"
    ) : (
    "https://${aws_cloudfront_distribution.dashboard.domain_name}"
  )
}

output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution serving the dashboard. Useful for `aws cloudfront create-invalidation` during local iteration."
  value       = aws_cloudfront_distribution.dashboard.id
}

output "dashboard_dns_target" {
  description = "CloudFront domain to CNAME / ALIAS your custom domain at when dns_provider = 'external'. Empty otherwise."
  value       = var.enable_custom_domain && var.dns_provider == "external" ? aws_cloudfront_distribution.dashboard.domain_name : ""
}

output "acm_validation_records" {
  description = "DNS records to create at your provider when dns_provider = 'external'. Empty list otherwise."
  value = var.enable_custom_domain && var.dns_provider == "external" ? [
    for dvo in aws_acm_certificate.dashboard[0].domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ] : []
}

output "api_custom_domain_target" {
  description = "Target hostname to CNAME api_custom_domain_name at when dns_provider = 'external'. Empty otherwise."
  value       = local.use_api_external_dns ? aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name : ""
}

output "api_acm_validation_records" {
  description = "DNS validation records for the API Gateway custom domain cert when dns_provider = 'external'. Empty otherwise."
  value = local.use_api_external_dns ? [
    for dvo in aws_acm_certificate.api[0].domain_validation_options : {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  ] : []
}

output "browser_application_id" {
  description = "GUID of the New Relic Browser application."
  value       = newrelic_browser_application.dashboard.id
}

output "synthetic_monitor_id" {
  description = "ID of the scripted browser synthetic monitor."
  value       = newrelic_synthetics_script_monitor.farm_manager.id
}

output "core_engine_url" {
  description = "HTTPS URL of the App Runner core-engine service."
  value       = "https://${aws_apprunner_service.core_engine.service_url}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for the core-engine image."
  value       = aws_ecr_repository.core_engine.repository_url
}

output "db_endpoint" {
  description = "Postgres endpoint (host:port) the core-engine connects to. Resolves to the RDS writer or the EC2 instance depending on var.use_ec2_postgres."
  value       = "${local.pg_host}:${local.pg_port}"
  sensitive   = true
}

output "db_backend" {
  description = "Which Postgres backend was provisioned: 'rds' (default) or 'ec2' (workaround)."
  value       = var.use_ec2_postgres ? "ec2" : "rds"
}

output "nr_layer_status" {
  description = "Snapshot of which NR Lambda layer is in use and how it compares to NR's published latest. Run `terraform output nr_layer_status` after apply to confirm — and when nr_layer_source = 'pinned', see the freshness check warning at plan time."
  value = {
    mode                        = var.nr_layer_source
    layer_name                  = local.nr_layer_name
    arn_in_use                  = local.lambda_layer_arn
    version_in_use              = local.nr_layer_version_in_use
    nr_published_latest_version = local.nr_layer_latest_version
    nr_published_latest_arn     = local.nr_layer_latest_arn
    is_up_to_date = (
      var.nr_layer_source != "pinned" ||
      local.nr_layer_latest_version == null ||
      var.new_relic_lambda_layer_version >= local.nr_layer_latest_version
    )
  }
}
