# =============================================================================
# core-engine on AWS App Runner (with ECR + VPC connector to RDS)
# =============================================================================

locals {
  core_engine_image_uri = "${aws_ecr_repository.core_engine.repository_url}:${var.core_engine_image_tag}"

  # Mirror of local.newrelic_lambda_env (lambdas.tf) for the App Runner runtime.
  newrelic_apprunner_env = {
    NEW_RELIC_LICENSE_KEY                            = var.new_relic_license_key
    NEW_RELIC_APP_NAME                               = "${var.name_prefix}-core-engine"
    NEW_RELIC_DISTRIBUTED_TRACING_ENABLED            = "true"
    NEW_RELIC_APPLICATION_LOGGING_FORWARDING_ENABLED = "true"
  }

  # Database connection details — resolved from whichever backend is active.
  # Each branch uses one(resource[*].attr) so the inactive branch (count=0)
  # evaluates to null instead of erroring on a missing index. The ternary on
  # var.use_ec2_postgres then picks the live value.
  pg_host     = var.use_ec2_postgres ? one(aws_instance.postgres[*].private_ip) : one(aws_db_instance.core_engine[*].address)
  pg_port     = var.use_ec2_postgres ? "5432" : tostring(one(aws_db_instance.core_engine[*].port))
  pg_user     = var.use_ec2_postgres ? "relifarm" : one(aws_db_instance.core_engine[*].username)
  pg_db       = var.use_ec2_postgres ? "relifarm" : one(aws_db_instance.core_engine[*].db_name)
  pg_password = random_password.db_master.result
}

# ---------------------------------------------------------------------------
# ECR repository for the core-engine image
# ---------------------------------------------------------------------------
resource "aws_ecr_repository" "core_engine" {
  name                 = "${var.name_prefix}-core-engine"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}

# ---------------------------------------------------------------------------
# Build + push the container image
#
# Same shape as null_resource.package_yield_forecast in lambdas.tf — content
# hash of every input file in the trigger map, single local-exec script.
# ---------------------------------------------------------------------------
resource "null_resource" "build_and_push_core_engine" {
  triggers = {
    dockerfile     = filesha256("${path.module}/../core-engine/Dockerfile")
    requirements   = filesha256("${path.module}/../core-engine/requirements.txt")
    newrelic_ini   = filesha256("${path.module}/../core-engine/newrelic.ini")
    main_py        = filesha256("${path.module}/../core-engine/app/main.py")
    db_py          = filesha256("${path.module}/../core-engine/app/db.py")
    models_py      = filesha256("${path.module}/../core-engine/app/models.py")
    simulator_py   = filesha256("${path.module}/../core-engine/app/simulator.py")
    init_sql       = filesha256("${path.module}/../core-engine/db/init.sql")
    repository_url = aws_ecr_repository.core_engine.repository_url
    image_tag      = var.core_engine_image_tag
  }

  provisioner "local-exec" {
    # When var.aws_profile is set, propagate it to `aws` and `docker` so the
    # ECR login uses the same identity as the Terraform provider. Empty string
    # leaves the subprocess to inherit the parent shell's credential env.
    environment = var.aws_profile != "" ? { AWS_PROFILE = var.aws_profile } : {}

    command = <<-EOT
      set -euo pipefail

      docker info >/dev/null 2>&1 || {
        echo "ERROR: Docker daemon not reachable. Start Docker Desktop and re-run terraform apply." >&2
        exit 1
      }

      ACCOUNT_ID="${data.aws_caller_identity.current.account_id}"
      REGION="${data.aws_region.current.name}"
      REPO_URL="${aws_ecr_repository.core_engine.repository_url}"
      TAG="${var.core_engine_image_tag}"

      aws ecr get-login-password --region "$REGION" \
        | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

      docker build --platform linux/amd64 -t "$REPO_URL:$TAG" "${path.module}/../core-engine"
      docker push "$REPO_URL:$TAG"
    EOT
  }
}

# ---------------------------------------------------------------------------
# IAM — App Runner needs two roles:
#   * access role: lets App Runner pull from ECR
#   * instance role: assumed by the running container (for future Secrets
#     Manager / other AWS service access)
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "apprunner_access_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_access" {
  name               = "${var.name_prefix}-apprunner-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_access_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_access_ecr" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

data "aws_iam_policy_document" "apprunner_instance_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_instance" {
  name               = "${var.name_prefix}-apprunner-instance"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_assume.json
}

# ---------------------------------------------------------------------------
# Networking — VPC connector lets App Runner reach RDS in the default VPC
# ---------------------------------------------------------------------------
resource "aws_security_group" "apprunner_egress" {
  name        = "${var.name_prefix}-apprunner-egress"
  description = "ReliFarm App Runner VPC connector egress"
  vpc_id      = data.aws_vpc.default.id

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Open RDS to traffic from the App Runner VPC connector only. Skipped when
# var.use_ec2_postgres = true — the EC2 path defines its own ingress rule
# against aws_security_group.postgres_ec2 in ec2_database.tf.
resource "aws_security_group_rule" "rds_from_apprunner" {
  count = var.use_ec2_postgres ? 0 : 1

  type                     = "ingress"
  security_group_id        = aws_security_group.rds[0].id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.apprunner_egress.id
}

# ---------------------------------------------------------------------------
# Internet egress for App Runner via NAT.
#
# App Runner with `egress_type = "VPC"` puts outbound traffic through ENIs in
# our subnets. App Runner ENIs do NOT get public IPs, so an IGW-only subnet
# leaves them unable to reach the internet (TCP-connect timeout). The default
# VPC has zero NAT gateways. This block adds:
#
#   - An EIP-backed NAT gateway in default-VPC subnet[0] (which keeps its IGW
#     route via the main RT — that's where the NAT gets its public-side
#     reachability).
#   - A private route table that points 0.0.0.0/0 at the NAT.
#   - Associations for subnets[1] and [2] to the private RT.
#
# We then narrow the VPC connector to subnets[1] and [2] only, so App Runner
# ENIs sit in NAT-routed subnets (they can't egress through a NAT in their
# own subnet — NAT requires source and gateway to be in different subnets).
#
# Subnet[0] keeps the IGW route, which is exactly what the EC2 Postgres in
# that subnet relies on for `dnf install` outbound.
# ---------------------------------------------------------------------------
resource "aws_eip" "apprunner_nat" {
  domain = "vpc"
  tags = {
    Name = "${var.name_prefix}-apprunner-nat"
  }
}

resource "aws_nat_gateway" "apprunner_egress" {
  allocation_id = aws_eip.apprunner_nat.id
  subnet_id     = data.aws_subnets.default.ids[0]

  tags = {
    Name = "${var.name_prefix}-apprunner-egress"
  }
}

resource "aws_route_table" "apprunner_private" {
  vpc_id = data.aws_vpc.default.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.apprunner_egress.id
  }

  tags = {
    Name = "${var.name_prefix}-apprunner-private"
  }
}

resource "aws_route_table_association" "apprunner_private" {
  for_each = toset(slice(data.aws_subnets.default.ids, 1, length(data.aws_subnets.default.ids)))

  subnet_id      = each.value
  route_table_id = aws_route_table.apprunner_private.id
}

resource "aws_apprunner_vpc_connector" "core_engine" {
  vpc_connector_name = "${var.name_prefix}-core-engine"

  # Skip subnet[0] — it hosts the NAT gateway. App Runner ENIs need to live
  # in NAT-routed subnets, which means subnets[1] and [2].
  subnets         = slice(data.aws_subnets.default.ids, 1, length(data.aws_subnets.default.ids))
  security_groups = [aws_security_group.apprunner_egress.id]

  # Ensure NAT routing is in place before the App Runner service starts
  # using this connector for outbound traffic.
  depends_on = [aws_route_table_association.apprunner_private]

  # Note on subnet/SG changes: App Runner blocks any new connector that
  # shares a security-group set with an existing connector — even at a
  # different name. So `create_before_destroy` doesn't work here. The clean
  # path when you change subnets/SGs is to destroy the App Runner service
  # first (which releases the connector), then let Terraform recreate both
  # from scratch:
  #   terraform apply -replace=aws_apprunner_service.core_engine
  # That ordering is destroy-service → destroy-connector → create-connector
  # → create-service, sidestepping the SG-uniqueness constraint entirely.
}

# ---------------------------------------------------------------------------
# App Runner service
# ---------------------------------------------------------------------------
resource "aws_apprunner_auto_scaling_configuration_version" "core_engine" {
  auto_scaling_configuration_name = "${var.name_prefix}-core-engine"
  min_size                        = 1
  max_size                        = 1
  max_concurrency                 = 100
}

resource "aws_apprunner_service" "core_engine" {
  service_name = "${var.name_prefix}-core-engine"

  source_configuration {
    auto_deployments_enabled = false

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }

    image_repository {
      image_identifier      = local.core_engine_image_uri
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"
        runtime_environment_variables = merge(local.newrelic_apprunner_env, {
          POSTGRES_HOST     = local.pg_host
          POSTGRES_PORT     = local.pg_port
          POSTGRES_USER     = local.pg_user
          POSTGRES_PASSWORD = local.pg_password
          POSTGRES_DB       = local.pg_db

          SIMULATION_INTERVAL_SECONDS = "5"
        })
      }
    }
  }

  instance_configuration {
    cpu               = var.core_engine_app_runner_cpu
    memory            = var.core_engine_app_runner_memory
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = aws_apprunner_vpc_connector.core_engine.arn
    }
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.core_engine.arn

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  # Both rds_from_apprunner and postgres_ec2_from_apprunner are count-gated
  # to opposite values of var.use_ec2_postgres — exactly one resolves to a
  # real instance, the other is an empty list and contributes no dependency.
  depends_on = [
    null_resource.build_and_push_core_engine,
    aws_security_group_rule.rds_from_apprunner,
    aws_security_group_rule.postgres_ec2_from_apprunner,
  ]
}
