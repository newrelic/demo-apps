# =============================================================================
# RDS Postgres for the core-engine
# =============================================================================
#
# Uses the account's default VPC + its default subnets. Postgres is private
# (publicly_accessible=false); the App Runner VPC connector reaches it via the
# security-group ingress rule below.

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# RDS-specific resources — count-gated so they vanish when the EC2 workaround
# path is selected. The shared bits (default VPC/subnets data sources, the
# generated password, and the Secrets Manager secret) stay un-gated below.
resource "aws_db_subnet_group" "core_engine" {
  count = var.use_ec2_postgres ? 0 : 1

  name       = "${var.name_prefix}-core-engine"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_security_group" "rds" {
  count = var.use_ec2_postgres ? 0 : 1

  name        = "${var.name_prefix}-rds"
  description = "ReliFarm core-engine RDS Postgres"
  vpc_id      = data.aws_vpc.default.id
}

# Ingress is added in core_engine.tf (after the App Runner egress SG exists)
# to break the SG dependency cycle.

resource "aws_security_group_rule" "rds_egress_all" {
  count = var.use_ec2_postgres ? 0 : 1

  type              = "egress"
  security_group_id = aws_security_group.rds[0].id
  protocol          = "-1"
  from_port         = 0
  to_port           = 0
  cidr_blocks       = ["0.0.0.0/0"]
}

# ---------------------------------------------------------------------------
# Master credentials — generated, kept in Secrets Manager
# ---------------------------------------------------------------------------
resource "random_password" "db_master" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_master" {
  name = "${var.name_prefix}-core-engine-db-master"

  # Force immediate deletion on destroy. Default (30) reserves the secret name
  # for 30 days after destroy, which blocks `terraform apply` from re-creating
  # a secret with the same name during a destroy/apply cycle. For a demo
  # stack that's destroyed and rebuilt frequently, immediate deletion is the
  # right trade-off; recovery-window protection isn't useful here.
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_master" {
  secret_id = aws_secretsmanager_secret.db_master.id
  # Reflects the active backend (RDS or EC2) via the locals defined in
  # core_engine.tf — the secret is always populated regardless of which path
  # var.use_ec2_postgres selects.
  secret_string = jsonencode({
    username = local.pg_user
    password = local.pg_password
    dbname   = local.pg_db
    host     = local.pg_host
    port     = local.pg_port
  })
}

# ---------------------------------------------------------------------------
# RDS instance
# ---------------------------------------------------------------------------
resource "aws_db_instance" "core_engine" {
  count = var.use_ec2_postgres ? 0 : 1

  identifier              = "${var.name_prefix}-core-engine"
  engine                  = "postgres"
  engine_version          = "16"
  instance_class          = var.db_instance_class
  allocated_storage       = var.db_allocated_storage
  storage_type            = "gp3"
  db_name                 = "relifarm"
  username                = "relifarm"
  password                = random_password.db_master.result
  db_subnet_group_name    = aws_db_subnet_group.core_engine[0].name
  vpc_security_group_ids  = [aws_security_group.rds[0].id]
  publicly_accessible     = false
  skip_final_snapshot     = true
  apply_immediately       = true
  deletion_protection     = false
  backup_retention_period = 0
  multi_az                = false
}
