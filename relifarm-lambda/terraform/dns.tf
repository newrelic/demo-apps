# =============================================================================
# Custom domain wiring (gated on var.enable_custom_domain)
# =============================================================================
#
# Two paths, picked by var.dns_provider:
#
#   "route53"  — Terraform creates the cert validation records and the alias
#                A-record automatically. Single `terraform apply`.
#
#   "external" — Terraform creates the cert and exposes the validation records
#                + the CloudFront target as outputs. The user provisions those
#                records at their DNS provider; once ACM marks the cert
#                "ISSUED", a second `terraform apply` wires it onto the
#                distribution.
#
# All ACM resources live in us-east-1 because CloudFront only consumes certs
# from that region (regardless of var.aws_region).

locals {
  use_custom_domain  = var.enable_custom_domain
  use_route53        = var.enable_custom_domain && var.dns_provider == "route53"
  use_external_dns   = var.enable_custom_domain && var.dns_provider == "external"
  custom_domain_apex = var.custom_domain_name

  # API Gateway custom domain — separately gated; user can opt into the
  # dashboard custom domain without the API one (they leave api_custom_domain_name = "").
  use_api_custom_domain = var.enable_custom_domain && length(var.api_custom_domain_name) > 0
  use_api_route53       = local.use_api_custom_domain && var.dns_provider == "route53"
  use_api_external_dns  = local.use_api_custom_domain && var.dns_provider == "external"

  # The CloudFront viewer_certificate dynamic block in frontend.tf reads this.
  # Route53 path uses the validated cert so apply waits for ISSUED status.
  # External path references the cert directly; first apply will fail to
  # finish the distribution until the user provisions validation records and
  # re-applies (ACM has marked the cert ISSUED by then).
  dashboard_acm_certificate_arn = local.use_route53 ? (
    length(aws_acm_certificate_validation.dashboard) > 0
    ? aws_acm_certificate_validation.dashboard[0].certificate_arn
    : ""
    ) : (
    length(aws_acm_certificate.dashboard) > 0
    ? aws_acm_certificate.dashboard[0].arn
    : ""
  )

  # Same pattern for the API Gateway regional cert. lambdas.tf reads this on
  # the aws_apigatewayv2_domain_name resource.
  api_acm_certificate_arn = local.use_api_route53 ? (
    length(aws_acm_certificate_validation.api) > 0
    ? aws_acm_certificate_validation.api[0].certificate_arn
    : ""
    ) : (
    length(aws_acm_certificate.api) > 0
    ? aws_acm_certificate.api[0].arn
    : ""
  )
}

# ---------------------------------------------------------------------------
# ACM certificate (always created when custom domain is enabled)
# ---------------------------------------------------------------------------
resource "aws_acm_certificate" "dashboard" {
  count    = local.use_custom_domain ? 1 : 0
  provider = aws.us_east_1

  domain_name       = local.custom_domain_apex
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ---------------------------------------------------------------------------
# Route53-managed validation + alias
# ---------------------------------------------------------------------------
resource "aws_route53_record" "cert_validation" {
  for_each = local.use_route53 ? {
    for dvo in aws_acm_certificate.dashboard[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60

  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "dashboard" {
  count    = local.use_route53 ? 1 : 0
  provider = aws.us_east_1

  certificate_arn         = aws_acm_certificate.dashboard[0].arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "dashboard_alias" {
  count = local.use_route53 ? 1 : 0

  zone_id = var.route53_zone_id
  name    = local.custom_domain_apex
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.dashboard.domain_name
    zone_id                = aws_cloudfront_distribution.dashboard.hosted_zone_id
    evaluate_target_health = false
  }
}

# ---------------------------------------------------------------------------
# API Gateway custom domain — regional ACM cert in var.aws_region
# (no us-east-1 alias needed; API Gateway HTTP APIs are regional).
# ---------------------------------------------------------------------------
resource "aws_acm_certificate" "api" {
  count = local.use_api_custom_domain ? 1 : 0

  domain_name       = var.api_custom_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = local.use_api_route53 ? {
    for dvo in aws_acm_certificate.api[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  zone_id = var.route53_zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60

  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "api" {
  count = local.use_api_route53 ? 1 : 0

  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

resource "aws_route53_record" "api_alias" {
  count = local.use_api_route53 ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.api_custom_domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
