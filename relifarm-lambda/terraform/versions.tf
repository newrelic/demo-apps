terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.62"
    }
    newrelic = {
      source  = "newrelic/newrelic"
      version = "~> 3.96"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.8"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.3"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.9"
    }
    http = {
      source  = "hashicorp/http"
      version = "~> 3.6"
    }
  }
}

locals {
  # Mirrors the New Relic entity tags in nr_entity_tags.tf, in AWS-conventional
  # TitleCase keys, so the AWS console/cost-allocation view stays consistent
  # with the NR entity view.
  common_aws_tags = {
    Team           = "ReliFarm Engineering"
    DeploymentTier = var.environment
    HeroChannel    = "help-relifarm-engineering"
    GithubRepo     = "https://github.com/newrelic/demo-apps/tree/main/relifarm-lambda"
    AppStack       = "relifarm"
    ManagedBy      = "terraform"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null

  default_tags {
    tags = local.common_aws_tags
  }
}

# CloudFront viewer certificates (ACM) must live in us-east-1 regardless of
# the deployment region. Resources that need a us-east-1 cert set
# `provider = aws.us_east_1`.
provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.aws_profile != "" ? var.aws_profile : null

  default_tags {
    tags = local.common_aws_tags
  }
}

provider "newrelic" {
  account_id = var.new_relic_account_id
  api_key    = var.new_relic_api_key
  region     = var.new_relic_region
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
