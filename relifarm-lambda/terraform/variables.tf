variable "aws_region" {
  description = "AWS region for Lambdas, API Gateway, and S3. Must be a region where AWS App Runner is available — the core-engine runs there."
  type        = string
  default     = "us-east-1"
}

# App Runner is regional; trying to deploy elsewhere fails with a DNS error
# mid-apply. We use a `check` block (Terraform 1.5+) rather than a variable
# `validation { }` so it emits a plan-time warning instead of hard-erroring.
# Hard-errors here would block `terraform destroy` if the existing state was
# created in a region the validation later rejected — leaving the operator
# unable to roll forward or back. Warn loudly, never trap.
# List per https://docs.aws.amazon.com/general/latest/gr/apprunner.html — bump
# when AWS adds a new region.
check "app_runner_region" {
  assert {
    condition = contains([
      "us-east-1", "us-east-2", "us-west-2",
      "eu-central-1", "eu-west-1",
      "ap-northeast-1", "ap-northeast-2",
      "ap-southeast-1", "ap-southeast-2",
    ], var.aws_region)
    error_message = "aws_region '${var.aws_region}' is not a region where AWS App Runner is available. The apply will fail when creating the App Runner service. Supported: us-east-1/2, us-west-2, eu-central-1, eu-west-1, ap-northeast-1/2, ap-southeast-1/2."
  }
}

# Named profile from ~/.aws/credentials or ~/.aws/config to use for AWS API
# calls. Leave empty ("") to fall back to the AWS provider's default credential
# chain (env vars → AWS_PROFILE → default profile → SSO → instance metadata).
# When set, this value is also exported as AWS_PROFILE for the `local-exec`
# scripts that build/push the core-engine ECR image, so the Terraform-managed
# auth and the docker/aws CLI subprocess auth stay aligned.
variable "aws_profile" {
  description = "Named AWS profile to use. Empty string uses the default credential chain (env vars / default profile / SSO)."
  type        = string
  default     = ""
}

variable "new_relic_account_id" {
  description = "Numeric New Relic account ID."
  type        = number
}

variable "new_relic_api_key" {
  description = "New Relic User API key (NRAK-...). Required for Terraform to provision NR resources."
  type        = string
  sensitive   = true
}

variable "new_relic_license_key" {
  description = "New Relic ingest license key. Stored as a Lambda environment variable."
  type        = string
  sensitive   = true
}

variable "new_relic_region" {
  description = "New Relic region: 'US' or 'EU'."
  type        = string
  default     = "US"

  validation {
    condition     = contains(["US", "EU"], var.new_relic_region)
    error_message = "new_relic_region must be 'US' or 'EU'."
  }
}

variable "name_prefix" {
  description = "Resource name prefix to allow multiple deployments in one account."
  type        = string
  default     = "relifarm"
}

variable "lambda_runtime" {
  description = "Lambda Python runtime."
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_mb" {
  description = "Lambda memory size."
  type        = number
  default     = 256
}

variable "lambda_timeout_seconds" {
  description = "Lambda timeout."
  type        = number
  default     = 15
}

# ---------------------------------------------------------------------------
# New Relic Lambda layer source
#
# Three modes (mutually exclusive):
#
#   "pinned"       (default) — reference NR's cross-account layer ARN at the
#                  version pinned in `new_relic_lambda_layer_version`. This
#                  repo's pin can drift behind NR's published latest; every
#                  plan checks NR's index and prints a loud warning when the
#                  pin is stale.
#
#   "auto-latest"  Fetch the latest published version at plan time from NR's
#                  index endpoint and use that. Always current, but adds a
#                  plan-time HTTP dependency on layers.newrelic-external.com.
#
#   "local"        Upload a downloaded copy of the layer zip into your own
#                  account as a private LayerVersion and point Lambda at
#                  that. Workaround for org SCPs that deny cross-account
#                  `lambda:GetLayerVersion`. Requires `local_nr_layer_zip_path`
#                  to point at a real file on disk.
#
# Repo maintenance note: this is a sample-app repo, not a continuously
# patched product. The pin in `new_relic_lambda_layer_version` will lag.
# The freshness check exists specifically so users on this repo find out at
# plan time, not via a silently-old layer in production-shaped demos.
# ---------------------------------------------------------------------------
variable "nr_layer_source" {
  description = "How to source the NR Python Lambda layer: 'pinned' (cross-account ARN at fixed version), 'auto-latest' (HTTP-fetch latest from NR index at plan time), or 'local' (private LayerVersion uploaded from a downloaded zip)."
  type        = string
  default     = "pinned"

  validation {
    condition     = contains(["pinned", "auto-latest", "local"], var.nr_layer_source)
    error_message = "nr_layer_source must be one of: 'pinned', 'auto-latest', 'local'."
  }
}

variable "new_relic_lambda_layer_version" {
  description = "Version of the NewRelicPython312 Lambda layer to use when nr_layer_source = 'pinned'. Ignored in 'auto-latest' and 'local' modes. NR publishes layer ARNs at https://layers.newrelic-external.com."
  type        = number
  default     = 82
}

variable "local_nr_layer_zip_path" {
  description = "Path (relative to the terraform module dir) to a downloaded NR Python Lambda layer zip. Required when nr_layer_source = 'local'. See README 'Workaround: locally-bundled NR Lambda layer' for the download command."
  type        = string
  default     = "../lambdas/newrelic-layer.zip"
}

variable "synthetic_locations" {
  description = "Public synthetic minion locations for the scripted browser monitor. Use the un-prefixed form (e.g. US_EAST_1, not AWS_US_EAST_1) — the NerdGraph API accepts both on write but reads back the un-prefixed form, so the prefixed form causes a perpetual diff in `terraform plan`."
  type        = list(string)
  default     = ["US_EAST_1", "EU_WEST_1"]
}

variable "synthetic_period" {
  description = "Synthetic monitor frequency."
  type        = string
  default     = "EVERY_5_MINUTES"
}

# ---------------------------------------------------------------------------
# core-engine on App Runner + RDS
# ---------------------------------------------------------------------------
variable "core_engine_image_tag" {
  description = "Tag pushed to ECR and pulled by App Runner."
  type        = string
  default     = "latest"
}

variable "core_engine_app_runner_cpu" {
  description = "App Runner instance CPU (e.g. '1024' = 1 vCPU)."
  type        = string
  default     = "1024"
}

variable "core_engine_app_runner_memory" {
  description = "App Runner instance memory in MB."
  type        = string
  default     = "2048"
}

variable "db_instance_class" {
  description = "RDS instance class for the core-engine Postgres."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB."
  type        = number
  default     = 20
}

# ---------------------------------------------------------------------------
# Database backend toggle
# Default = RDS Postgres (recommended).
# Flip to true to self-host Postgres on a t4g.micro EC2 instance instead — a
# workaround for AWS accounts where rds:CreateDBInstance is denied by an SCP.
# When true, the RDS resources are skipped entirely and the App Runner
# core-engine connects to the EC2 instance over the default VPC.
# ---------------------------------------------------------------------------
variable "use_ec2_postgres" {
  description = "Self-host Postgres on EC2 instead of RDS. Workaround for accounts where rds:CreateDBInstance is denied by an SCP. Default false = RDS."
  type        = bool
  default     = false
}

variable "ec2_postgres_instance_type" {
  description = "EC2 instance type used when use_ec2_postgres = true. Must be ARM64 to match the AL2023 ARM AMI lookup."
  type        = string
  default     = "t4g.micro"
}

variable "ec2_postgres_volume_size_gb" {
  description = "Root EBS volume size (GiB) for the EC2 Postgres instance. Must be >= the AL2023 ARM AMI's snapshot size (currently 30 GiB). Bump if a future AMI snapshot grows past this default."
  type        = number
  default     = 30
}

# ---------------------------------------------------------------------------
# Frontend custom domain (optional)
# Default deployment serves the dashboard from a CloudFront distribution at
# *.cloudfront.net (HTTPS, no domain needed). Set `enable_custom_domain = true`
# to map a domain you control onto the same distribution.
# ---------------------------------------------------------------------------
variable "enable_custom_domain" {
  description = "If true, provision an ACM cert and map var.custom_domain_name onto the dashboard CloudFront distribution."
  type        = bool
  default     = false
}

variable "custom_domain_name" {
  description = "Domain to point at the dashboard (e.g. 'dash.example.com'). Required when enable_custom_domain = true."
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_custom_domain || length(var.custom_domain_name) > 0
    error_message = "custom_domain_name must be set when enable_custom_domain = true."
  }
}

variable "dns_provider" {
  description = "Where the dashboard's DNS records live: 'route53' (Terraform writes them) or 'external' (Terraform outputs them for you to create at your DNS provider)."
  type        = string
  default     = "route53"

  validation {
    condition     = contains(["route53", "external"], var.dns_provider)
    error_message = "dns_provider must be 'route53' or 'external'."
  }
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID for var.custom_domain_name. Required when enable_custom_domain = true and dns_provider = 'route53'."
  type        = string
  default     = ""

  validation {
    condition     = !(var.enable_custom_domain && var.dns_provider == "route53") || length(var.route53_zone_id) > 0
    error_message = "route53_zone_id must be set when enable_custom_domain = true and dns_provider = 'route53'."
  }
}

variable "api_custom_domain_name" {
  description = "Optional custom domain to map onto the API Gateway HTTP API (e.g. 'api.example.com'). Only takes effect when enable_custom_domain = true. Empty string leaves API Gateway on its default *.execute-api URL."
  type        = string
  default     = ""
}
