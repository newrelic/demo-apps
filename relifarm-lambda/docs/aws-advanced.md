# Advanced AWS topics

This file collects the deployment paths and configuration knobs that the main
[README](../README.md) does not need on the happy path. Reach for it when:

* Your AWS org's service control policy denies `rds:CreateDBInstance` or
  cross-account `lambda:GetLayerVersion` (jump to
  [EC2 Postgres fallback](#ec2-postgres-fallback) or
  [Locally-bundled NR Lambda layer](#locally-bundled-nr-lambda-layer)).
* The pinned NR Lambda layer version in this repo has gone stale.
* You want to put your own domain in front of the dashboard or API.

For an error you've already hit, start at [troubleshooting.md](troubleshooting.md).

---

## Table of contents

- [NR Lambda layer source — pinned, auto-latest, or locally bundled](#nr-lambda-layer-source--pinned-auto-latest-or-locally-bundled)
  - [Stale pin? You'll see this on every `terraform plan`](#stale-pin-youll-see-this-on-every-terraform-plan)
  - [Locally-bundled NR Lambda layer](#locally-bundled-nr-lambda-layer)
- [EC2 Postgres fallback](#ec2-postgres-fallback)
- [Optional: Custom Domain](#optional-custom-domain)
  - [Route53 path](#route53-path)
  - [External DNS path](#external-dns-path)

---

## NR Lambda layer source — pinned, auto-latest, or locally bundled

The two Lambdas (`yield-forecast`, `valve-scheduler`) use the New Relic
Python Lambda layer for auto-instrumentation. By default Terraform references
NR's cross-account published layer ARN at a *pinned* version. Three reasons
you might want to change that:

1. The pin in this repo has gone stale (this is a sample-app repo, not a
   continuously patched product).
2. You want to track NR's latest automatically.
3. Your AWS org's SCP denies cross-account `lambda:GetLayerVersion`, so the
   pinned/auto-latest paths both fail at apply time with `AccessDeniedException`.

The `nr_layer_source` variable in `terraform.tfvars` selects between three
modes:

| Mode             | What it does                                                                                          | When to use                                                       |
|------------------|-------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| `pinned` (default) | References NR's cross-account ARN at `var.new_relic_lambda_layer_version`. Plan-time freshness check warns loudly when stale. | You want deterministic IaC. The drift warning is your nudge to bump the pin. |
| `auto-latest`    | Fetches the latest version from `https://<region>.layers.newrelic-external.com/get-layers?...` at plan time and uses that ARN. | You want to always be on NR's latest. Adds a plan-time HTTP dependency. |
| `local`          | Reads a downloaded layer zip from disk and uploads it as a private `LayerVersion` in your own AWS account. The Lambdas reference *that* ARN. | Your account's SCP denies cross-account `lambda:GetLayerVersion`. |

### Stale pin? You'll see this on every `terraform plan`

```
╷
│ Warning: Check block assertion failed
│
│   on lambdas.tf line 110, in check "nr_layer_currency":
│
│ ============================================================================
│   NEW RELIC LAMBDA LAYER VERSION DRIFT
│ ============================================================================
│   Repo pin:      NewRelicPython312:82
│   NR latest:     NewRelicPython312:91
│   Behind by:     9 version(s)
│   ...
│   To upgrade in place, set in terraform.tfvars:
│     new_relic_lambda_layer_version = 91
│   To track NR's latest automatically:
│     nr_layer_source = "auto-latest"
│ ============================================================================
╵
```

Run `terraform output nr_layer_status` after any apply to inspect mode,
version-in-use, NR's published latest, and the resolved ARN.

### Locally-bundled NR Lambda layer

This is the SCP-denial workaround. The pattern: download the layer zip once
from a context where you have permission, then point Terraform at it.

Active Layers for New Relic can be found here: https://layers.newrelic-external.com/

```bash
# 1. From a session with cross-account lambda:GetLayerVersion permission
#    (e.g. a non-SSO IAM user not bound by the org SCP):
LAYER_VERSION=82       # or whatever you'd otherwise pin
LAYER_REGION=us-east-1
LAYER_NAME=NewRelicPython312

DOWNLOAD_URL=$(aws lambda get-layer-version-by-arn \
  --arn "arn:aws:lambda:${LAYER_REGION}:451483290750:layer:${LAYER_NAME}:${LAYER_VERSION}" \
  --query 'Content.Location' --output text)

curl -L "$DOWNLOAD_URL" -o relifarm-lambda/lambdas/newrelic-layer.zip

# 2. Opt in via terraform.tfvars:
#      nr_layer_source = "local"
#      local_nr_layer_zip_path = "../lambdas/newrelic-layer.zip"   # default; override only if you put it elsewhere

# 3. Apply.
terraform apply
```

Once the zip is on disk, Terraform creates an `aws_lambda_layer_version` in
*your* account named `${name_prefix}-newrelic-python-local`. Bumping the zip
(downloading a newer version and replacing the file) changes
`source_code_hash`, which causes Terraform to publish a new LayerVersion and
roll the Lambdas onto it on the next apply.

The downloaded zip is gitignored — it's a multi-MB binary that doesn't
belong in source control.

---

## EC2 Postgres fallback

By default Terraform provisions an RDS Postgres instance for the core-engine.
Some AWS accounts deny `rds:CreateDBInstance` (and the rest of the RDS API)
via an org-level service control policy that you can't get an exception for.
For those accounts, set:

```hcl
# terraform.tfvars
use_ec2_postgres = true
```

Terraform will then skip the RDS resources entirely and instead provision a
single `t4g.micro` EC2 instance running Amazon Linux 2023, install Postgres
16 from `dnf` via cloud-init, create the `relifarm` role and database, and
expose port 5432 to the App Runner VPC connector via a security group. The
core-engine connects to this instance over the default VPC; everything
downstream (NR psycopg2 auto-instrumentation, the trace_id persistence trick,
the schema bootstrap on first boot) works identically.

Trade-offs vs. RDS:

* **No managed backups** — the EBS volume is the only copy. Take manual
  snapshots if you care about durability beyond a demo session.
* **Single-AZ, single instance** — no failover. If the EC2 dies, you lose
  state until `terraform apply` rebuilds it from scratch.
* **First-boot fragility** — the user-data script bootstraps Postgres once.
  If `dnf install` or `postgresql-setup --initdb` fails (e.g., a transient
  AL2023 repo hiccup), the apply succeeds but the core-engine can't
  connect. SSH-in via SSM to debug:

  ```bash
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=relifarm-postgres" \
    --query "Reservations[].Instances[].InstanceId" --output text)
  aws ssm start-session --target "$INSTANCE_ID"
  # On the instance:
  sudo cat /var/log/cloud-init-output.log
  sudo systemctl status postgresql
  sudo -iu postgres psql -c '\l'   # verify the relifarm database exists
  ```

* **No SSH key needed** — the instance has the `AmazonSSMManagedInstanceCore`
  managed policy attached and is reached via SSM Session Manager.

If you ever switch back (`use_ec2_postgres = false`), `terraform apply` will
destroy the EC2 + SG + IAM and re-create the RDS path from scratch — data
doesn't migrate between paths. `terraform output db_backend` confirms which
path is currently active.

---

## Optional: Custom Domain

By default the dashboard is served from a CloudFront-assigned domain
(`*.cloudfront.net`) over HTTPS and the browser fetches go to the
`*.execute-api.amazonaws.com` URL — no domain or DNS work required. To put
your own domain in front of either or both, set these in `terraform.tfvars`:

```hcl
enable_custom_domain   = true
custom_domain_name     = "dash.example.com"
api_custom_domain_name = "api.example.com"   # optional; omit to keep *.execute-api
dns_provider           = "route53"           # or "external"
route53_zone_id        = "Z01234567ABCDEFGHIJKL"   # only when dns_provider = "route53"
```

`api_custom_domain_name` is independent of `custom_domain_name` — set just
the dashboard, just the API, or both. When the API custom domain is in play,
the dashboard's fetch calls and the synthetic monitor automatically retarget
to it (so DevTools and synthetic logs show `api.example.com` instead of
`*.execute-api`).

### Route53 path

Single `terraform apply`. Terraform creates each ACM
certificate (dashboard cert in us-east-1 for CloudFront, API cert in your
deployment region for API Gateway), writes the validation records and the
alias A-records into the same Route53 zone, and binds the certs onto
CloudFront and the API Gateway domain.

### External DNS path

Two-pass `terraform apply`:

1. First apply provisions the ACM cert(s) and outputs the validation records.
   When both domains are set, you'll have two record sets to create:
   ```bash
   terraform apply
   terraform output acm_validation_records       # dashboard cert validation
   terraform output api_acm_validation_records   # API Gateway cert validation
   terraform output dashboard_dns_target         # CloudFront target
   terraform output api_custom_domain_target     # API Gateway target
   ```
2. Create the validation records at your DNS provider. Wait for ACM to mark
   each cert `ISSUED` (usually a few minutes).
3. Re-run `terraform apply` to bind the validated certs onto CloudFront and
   the API Gateway domain, then create CNAME/ALIAS records pointing
   `dash.example.com` at `dashboard_dns_target` and `api.example.com` at
   `api_custom_domain_target`.

> If you used `dns_provider = "external"`, the validation records and
> target records you created at your DNS provider stay in place after a
> `terraform destroy` until you remove them manually.
