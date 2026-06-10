# =============================================================================
# Browser app + dashboard hosting (private S3 fronted by CloudFront)
# =============================================================================
#
# Layout:
#   [Browser] -- HTTPS --> [CloudFront] -- OAC --> [private S3 bucket]
#
# The S3 bucket has every public-access flag set; only the CloudFront
# distribution can read its objects, gated by a bucket policy that pins the
# allowed source ARN to this distribution.

# Browser app — receives RUM data from the dashboard.
resource "newrelic_browser_application" "dashboard" {
  name                        = "${var.name_prefix}-web-dash"
  cookies_enabled             = true
  distributed_tracing_enabled = true
  # NerdGraph's AgentApplicationBrowserLoader enum: SPA = the modern Pro+SPA
  # loader (DT-on-fetch, route-change tracking). The legacy "PRO_SPA" string
  # is no longer accepted by the API.
  loader_type = "SPA"
}

# ---------------------------------------------------------------------------
# Private S3 bucket for the dashboard assets
# ---------------------------------------------------------------------------
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "dashboard" {
  bucket        = "${var.name_prefix}-web-dash-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "dashboard" {
  bucket                  = aws_s3_bucket.dashboard.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ---------------------------------------------------------------------------
# Render index.html — substitute browser snippet, core-engine URL, and
# yield-forecast URL into placeholder tokens.
# ---------------------------------------------------------------------------
locals {
  # The newrelic_browser_application.js_config attribute returns the bare
  # {info, init, loader_config} JSON object — not a wrapped <script> snippet.
  # Wrap it ourselves and pair with the SPA-flavoured loader CDN URL (matches
  # loader_type = "SPA" set on the resource above). Older provider versions
  # returned a fully-wrapped snippet; the modern provider normalised this to
  # JSON-only, so the dashboard template needs us to construct the wrapper.
  browser_snippet = <<-EOT
    <script type="text/javascript">
    ;window.NREUM=${newrelic_browser_application.dashboard.js_config};
    </script>
    <script src="https://js-agent.newrelic.com/nr-loader-spa-current.min.js"></script>
  EOT

  index_rendered = replace(
    replace(
      replace(
        file("${path.module}/../web-dash/index.html"),
        "%%NEW_RELIC_BROWSER_SNIPPET%%",
        local.browser_snippet
      ),
      "%%CORE_ENGINE_URL%%",
      "https://${aws_apprunner_service.core_engine.service_url}"
    ),
    "%%YIELD_FORECAST_URL%%",
    local.yield_forecast_url
  )
}

resource "aws_s3_object" "index" {
  bucket       = aws_s3_bucket.dashboard.id
  key          = "index.html"
  content      = local.index_rendered
  content_type = "text/html"
  etag         = md5(local.index_rendered)

  # index.html re-renders whenever the upstream URLs / NR snippet change;
  # disable browser caching so the dashboard picks up new endpoints quickly.
  cache_control = "no-store, max-age=0"
}

resource "aws_s3_object" "styles" {
  bucket       = aws_s3_bucket.dashboard.id
  key          = "styles.css"
  source       = "${path.module}/../web-dash/styles.css"
  content_type = "text/css"
  etag         = filemd5("${path.module}/../web-dash/styles.css")
}

resource "aws_s3_object" "appjs" {
  bucket       = aws_s3_bucket.dashboard.id
  key          = "app.js"
  source       = "${path.module}/../web-dash/app.js"
  content_type = "application/javascript"
  etag         = filemd5("${path.module}/../web-dash/app.js")
}

# ---------------------------------------------------------------------------
# CloudFront distribution
# ---------------------------------------------------------------------------
resource "aws_cloudfront_origin_access_control" "dashboard" {
  name                              = "${var.name_prefix}-web-dash"
  description                       = "OAC for the ReliFarm dashboard S3 origin"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "dashboard" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name_prefix} dashboard"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  # When enable_custom_domain = true, register the user-supplied alias.
  aliases = var.enable_custom_domain ? [var.custom_domain_name] : []

  origin {
    domain_name              = aws_s3_bucket.dashboard.bucket_regional_domain_name
    origin_id                = "s3-dashboard"
    origin_access_control_id = aws_cloudfront_origin_access_control.dashboard.id
  }

  default_cache_behavior {
    target_origin_id       = "s3-dashboard"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    # Managed CachingOptimized policy — fine for static JS/CSS; index.html
    # carries `Cache-Control: no-store` from the S3 object so updates surface.
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6"
  }

  # SPA fallback: 403/404 from S3 returns the index so client-side state
  # survives a refresh on a deep link.
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }
  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Two-pronged viewer cert:
  #   - default (no domain): use the CloudFront default cert at *.cloudfront.net
  #   - custom domain: bind the ACM cert validated in dns.tf
  dynamic "viewer_certificate" {
    for_each = var.enable_custom_domain ? [] : [1]
    content {
      cloudfront_default_certificate = true
    }
  }

  dynamic "viewer_certificate" {
    for_each = var.enable_custom_domain ? [1] : []
    content {
      acm_certificate_arn      = local.dashboard_acm_certificate_arn
      ssl_support_method       = "sni-only"
      minimum_protocol_version = "TLSv1.2_2021"
    }
  }
}

# ---------------------------------------------------------------------------
# Bucket policy — only this CloudFront distribution can GetObject
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "dashboard_oac" {
  statement {
    sid     = "AllowCloudFrontReadViaOAC"
    actions = ["s3:GetObject"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    resources = ["${aws_s3_bucket.dashboard.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.dashboard.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id
  policy = data.aws_iam_policy_document.dashboard_oac.json

  depends_on = [aws_s3_bucket_public_access_block.dashboard]
}
