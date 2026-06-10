# =============================================================================
# Self-hosted Postgres on EC2 — opt-in workaround for SCP-denied accounts
# =============================================================================
#
# Activated by var.use_ec2_postgres = true. Every resource below is
# count-gated, so when the flag is off this whole file contributes nothing to
# the plan. The companion RDS resources in database.tf use the inverse gate.
#
# Layout when active:
#   [App Runner VPC connector] -- 5432 --> [aws_security_group.postgres_ec2]
#                                          [aws_instance.postgres]   t4g.micro
#                                                                    AL2023 ARM64
#                                                                    PG 16 via dnf
#
# Debugging path is SSM Session Manager (no SSH keys needed):
#   aws ssm start-session --target <instance-id>

# ---------------------------------------------------------------------------
# AMI: latest Amazon Linux 2023 ARM64 — matches the t4g.* instance family.
# ---------------------------------------------------------------------------
data "aws_ami" "al2023_arm64" {
  count = var.use_ec2_postgres ? 1 : 0

  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
}

# ---------------------------------------------------------------------------
# Security group — accept 5432 only from the App Runner egress SG.
# ---------------------------------------------------------------------------
resource "aws_security_group" "postgres_ec2" {
  count = var.use_ec2_postgres ? 1 : 0

  name        = "${var.name_prefix}-postgres-ec2"
  description = "ReliFarm self-hosted Postgres on EC2 (workaround path)"
  vpc_id      = data.aws_vpc.default.id

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "postgres_ec2_from_apprunner" {
  count = var.use_ec2_postgres ? 1 : 0

  type                     = "ingress"
  security_group_id        = aws_security_group.postgres_ec2[0].id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
  source_security_group_id = aws_security_group.apprunner_egress.id
}

# ---------------------------------------------------------------------------
# IAM — instance role with SSM Session Manager. No SSH key required.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "postgres_ec2_assume" {
  count = var.use_ec2_postgres ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "postgres_ec2" {
  count = var.use_ec2_postgres ? 1 : 0

  name               = "${var.name_prefix}-postgres-ec2"
  assume_role_policy = data.aws_iam_policy_document.postgres_ec2_assume[0].json
}

resource "aws_iam_role_policy_attachment" "postgres_ec2_ssm" {
  count = var.use_ec2_postgres ? 1 : 0

  role       = aws_iam_role.postgres_ec2[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "postgres_ec2" {
  count = var.use_ec2_postgres ? 1 : 0

  name = "${var.name_prefix}-postgres-ec2"
  role = aws_iam_role.postgres_ec2[0].name
}

# ---------------------------------------------------------------------------
# EC2 instance — t4g.micro, root EBS gp3 (size mirrors var.db_allocated_storage),
# user-data installs Postgres 16 from AL2023's dnf repo and bootstraps the
# relifarm user + database.
# ---------------------------------------------------------------------------
resource "aws_instance" "postgres" {
  count = var.use_ec2_postgres ? 1 : 0

  ami                    = data.aws_ami.al2023_arm64[0].id
  instance_type          = var.ec2_postgres_instance_type
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.postgres_ec2[0].id]
  iam_instance_profile   = aws_iam_instance_profile.postgres_ec2[0].name

  # Default VPC subnets route 0.0.0.0/0 to the IGW, but an instance still
  # needs a public IP for outbound NAT to actually work. Without it the
  # instance can't reach the AL2023 dnf mirrors (postgresql16-server install
  # fails) or the SSM endpoints (Session Manager won't connect). The default
  # VPC has no NAT gateway, so the cheapest fix is a public IP. Inbound
  # 5432 stays restricted to the App Runner egress SG via
  # aws_security_group_rule.postgres_ec2_from_apprunner.
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp3"
    volume_size = var.ec2_postgres_volume_size_gb
    encrypted   = true
  }

  user_data = templatefile("${path.module}/templates/postgres_user_data.sh.tftpl", {
    db_password = random_password.db_master.result
    db_user     = "relifarm"
    db_name     = "relifarm"
    vpc_cidr    = data.aws_vpc.default.cidr_block
  })

  # user-data only runs on first boot; replacing the instance on script changes
  # is the only way to re-bootstrap.
  user_data_replace_on_change = true

  tags = {
    Name = "${var.name_prefix}-postgres"
  }
}
