# Troubleshooting

Errors you might hit while deploying ReliFarm, organised first as a
**symptom → cause → fix** decision tree, then as a catalog of the literal
error strings you might see in `terraform apply` output.

For configuration knobs that switch between deploy modes (RDS vs. EC2,
Lambda layer source, custom domain), see
[aws-advanced.md](aws-advanced.md).

---

## Decision tree

### "I ran `docker compose up` and the core-engine container exited"

* **Most common cause**: `NEW_RELIC_LICENSE_KEY` in `.env` is still the
  placeholder value or is empty.
  **Fix**: open `.env`, replace `<your_ingest_license_key>` with your real
  ingest key (the one ending in `NRAL`), then `docker compose down && docker compose up`.
* **Next most common**: Postgres healthcheck failed because the data volume
  has stale credentials from a previous run.
  **Fix**: `docker compose down --volumes` and re-run.

### "`terraform apply` failed within the first minute"

Almost always one of:

* **Docker Desktop isn't running** — see "Docker daemon not reachable" below.
* **AWS credentials don't resolve** — `aws sts get-caller-identity` will
  reproduce the error. Re-export `AWS_PROFILE` or `aws sso login`.
* **`aws_region` doesn't support App Runner** — see "`apprunner.<region>` no such host" below.
* **`terraform.tfvars` has placeholder NR keys** — Terraform validates the
  format of `NEW_RELIC_API_KEY` (must start with `NRAK-`) and the license
  key (must end with `NRAL`).

### "`terraform apply` failed 5+ minutes in"

* **At `aws_db_instance.core_engine`**: your account denies RDS. Switch to
  the EC2 fallback — see [aws-advanced.md#ec2-postgres-fallback](aws-advanced.md#ec2-postgres-fallback).
* **At `aws_lambda_layer_version` lookup**: your account denies cross-account
  `lambda:GetLayerVersion`. Switch to the local-bundle layer mode —
  see [aws-advanced.md#locally-bundled-nr-lambda-layer](aws-advanced.md#locally-bundled-nr-lambda-layer).
* **At `aws_secretsmanager_secret.db_master`**: see "Secrets Manager already
  scheduled for deletion" below.
* **At `aws_apprunner_service.core_engine`**: the image push to ECR
  succeeded but App Runner can't pull/start it. Check the App Runner
  service logs in the AWS console; usually a NAT-gateway egress problem
  (see "Core-engine APM agent silently fails to register" below).

### "`terraform apply` finished but the dashboard is blank / 403 / no data"

* **403 from CloudFront**: the OAC is configured but the S3 upload race lost.
  Re-run `terraform apply`; it's idempotent.
* **Dashboard loads but tables stay empty**: the core-engine isn't
  reachable from the browser. Open DevTools → Network and click on a
  failing `/sectors` request. If it's a CORS error, the API Gateway
  CORS allowlist isn't picking up the dashboard origin — check
  `terraform output dashboard_url` matches what your browser shows.
* **Dashboard loads, data flows, but no `relifarm-core-engine` entity in
  NR**: see "Core-engine APM agent silently fails to register" below.

### "I want to start over"

```bash
cd terraform && terraform destroy
cd ../core-engine && docker compose --env-file ../.env down --volumes
rm -rf ../lambdas/*/package ./build
```

---

## Error catalog

### `creating Secrets Manager Secret ... InvalidRequestException: ... already scheduled for deletion`

This shows up on a fresh `terraform apply` if you previously destroyed the
stack and are recreating it. AWS Secrets Manager doesn't actually delete
secrets immediately — by default, deletion is *scheduled* for 7–30 days
later (a recovery window in case you accidentally deleted production data).
During that window the secret name is reserved, and a new secret with the
same name can't be created.

The terraform code now sets `recovery_window_in_days = 0` on
`aws_secretsmanager_secret.db_master` so future destroys delete immediately.
For an existing reservation that's already in the recovery window, force-
delete via the CLI:

```bash
aws secretsmanager delete-secret \
  --secret-id "$(terraform console <<<'var.name_prefix' | tr -d '"')-core-engine-db-master" \
  --force-delete-without-recovery
# then:
terraform apply
```

If `terraform console` isn't convenient, just substitute the literal name —
e.g. `relifarm-core-engine-db-master` for the default `name_prefix`, or
`<your-prefix>-core-engine-db-master` if you set a custom one in
`terraform.tfvars`.

### `dial tcp: lookup apprunner.<region>.amazonaws.com: no such host`

App Runner isn't available in the region you set. Supported regions:
`us-east-1`, `us-east-2`, `us-west-2`, `eu-central-1`, `eu-west-1`,
`ap-northeast-1`, `ap-northeast-2`, `ap-southeast-1`, `ap-southeast-2`.
Edit `aws_region` in `terraform.tfvars` and re-apply.

### `failed to connect to the docker API at unix:///.../docker.sock`

Docker Desktop isn't running. Start it and re-run `terraform apply`.

### `lambda:GetLayerVersion` AccessDenied on the cross-account NR layer ARN

Your AWS org SCP denies cross-account Lambda layer access. Switch to the
local-bundle workaround per
[aws-advanced.md#locally-bundled-nr-lambda-layer](aws-advanced.md#locally-bundled-nr-lambda-layer)
(`nr_layer_source = "local"`).

### `explicit deny in a service control policy` at `aws_db_instance.core_engine`

Your AWS org SCP denies RDS. Switch to the EC2 Postgres path — see
[aws-advanced.md#ec2-postgres-fallback](aws-advanced.md#ec2-postgres-fallback)
(`use_ec2_postgres = true`).

### Core-engine APM agent silently fails to register

Symptom: in NR, you don't see `relifarm-core-engine` as an APM entity. In
the App Runner application logs you see only:

```
newrelic.core.agent INFO - New Relic Python Agent (...)
... (long silence) ...
newrelic.core.application WARNING - Registration of the application
'relifarm-core-engine' with the data collector failed after multiple attempts.
```

That gap is a TCP-connect timeout that the agent swallows. Root cause: the
App Runner service runs with `egress_type = "VPC"`, which routes outbound
traffic through ENIs in your VPC subnets — and **App Runner ENIs never get
public IPs**. With only an IGW route in the default VPC's main route table,
the ENIs have no return path for outbound packets to `collector.newrelic.com`.

The Terraform stack provisions a NAT gateway specifically to fix this:

* `aws_eip.apprunner_nat` — Elastic IP fronted by Cloudfront/Fastly/whatever NR routes through.
* `aws_nat_gateway.apprunner_egress` — placed in default-VPC subnet[0] (which keeps its IGW route via the main RT, so the NAT itself can reach the internet).
* `aws_route_table.apprunner_private` with `0.0.0.0/0 → NAT`.
* `aws_route_table_association.apprunner_private` for default-VPC subnets[1] and [2] — these become the NAT-routed "private" subnets.
* `aws_apprunner_vpc_connector.core_engine.subnets` is restricted to subnets[1] and [2]: App Runner ENIs sit in NAT-routed subnets, never in the same subnet as the NAT itself (NAT requires source and gateway to be in different subnets).

If you redeploy this stack into a non-default VPC that already has a NAT
gateway, you can simplify by pointing the VPC connector at any pre-existing
private subnets and dropping the NAT resources from `terraform/core_engine.tf`.

**Cost note**: a NAT gateway is roughly $32/month plus ~$0.062/GB processed.
For low-volume demo traffic that's about $1/day.

**App Runner replacement gotcha**: changing the VPC connector's `subnets`
or `security_groups` forces resource replacement, but App Runner refuses to
create a new connector that shares a security-group set with an existing one
— even with `create_before_destroy`. The clean workflow when changing those
attributes is:

```bash
terraform apply -replace='aws_apprunner_service.core_engine'
```

That ordering destroys the service first (releasing the connector), then
the connector, then recreates both.
