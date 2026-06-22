# FAQ

Common questions SEs hear from customers about the ReliFarm demo. Lean on
these in pre-meeting prep.

---

### Why does this stack need a NAT gateway? Isn't that expensive?

Yes — the NAT gateway is roughly $32/month and is the single biggest line
item on the AWS bill. We need it because App Runner is configured with
`egress_type = "VPC"` so the core-engine can reach RDS over private
networking, and App Runner ENIs in a VPC connector never get public IPs.
Without the NAT, the NR Python APM agent inside the container can't reach
`collector.newrelic.com` and you'd see the `relifarm-core-engine` entity
silently fail to register.

If you're redeploying into a customer account that already has a NAT
(e.g. a non-default VPC with one), you can drop the NAT resources from
`terraform/core_engine.tf` and point `aws_apprunner_vpc_connector` at the
existing private subnets.

### Can I deploy this without RDS?

Yes. Set `use_ec2_postgres = true` in `terraform.tfvars`. Terraform will
self-host Postgres on a `t4g.micro` EC2 instance instead. We built this
specifically for AWS accounts where org SCPs deny `rds:CreateDBInstance`.
See [aws-advanced.md → EC2 Postgres fallback](aws-advanced.md#ec2-postgres-fallback)
for trade-offs.

### How do I show this to a customer who doesn't have AWS access?

Two options:

* **Run AWS-deploy in your own demo account, share the dashboard URL.**
  Cheapest if you'll demo many times — pay $1–$2/day while the stack is
  up, tear it down between demos.
* **Run only the local Docker Compose path during the meeting.** The
  core-engine + Postgres will run on your laptop and you can show the
  `relifarm-core-engine` APM entity, transactions, and DB spans live.
  You won't be able to show the Browser Agent, Lambdas, distributed
  tracing across the four hops, or the synthetic monitor on this path.

### Can the dashboard be on our own domain?

Yes. Set `enable_custom_domain = true` and the related variables in
`terraform.tfvars`. Both Route53 and external DNS providers are
supported (external DNS requires a two-pass apply). See
[aws-advanced.md → Optional: custom domain](aws-advanced.md#optional-custom-domain).

### How do I prove the trace really crosses all four hops?

Trigger an irrigation run from the dashboard, then in NR open the
`relifarm-core-engine` entity → click the latest `POST /executions`
transaction. The Distributed Tracing waterfall will show:

```
Browser/click → APIGatewayV2 → yield-forecast → APIGatewayV2
              → valve-scheduler → POST /executions → core-engine → Postgres
```

The trace ID is also surfaced in the dashboard's network response and is
persisted to the `irrigation_executions.trace_id` column, so you can
demonstrate "find the user-visible trace_id, then jump to that exact trace
in NR."

### How long does first-data take in NR after `terraform apply`?

* APM (core-engine, Lambdas): ~2–5 minutes after the App Runner service
  finishes starting and gets its first request.
* Browser app: appears as soon as the first dashboard pageview lands.
* Synthetic monitor: first run within ~5 minutes of apply finishing.

If nothing shows up after 10 minutes, head to
[troubleshooting.md](troubleshooting.md).

### Why two Lambdas and an App Runner service? Why not just one Lambda?

The shape exists to surface every NR feature in one demo: Lambda Layers,
Browser Agent, native Python APM agent, distributed tracing across
synchronous service-to-service calls, logs-in-context, errors inbox, and
synthetic monitoring. A single-service demo wouldn't exercise the
cross-service trace propagation story, which is usually what customers
care most about.

### Can I change the simulation cadence or error-injection rate?

Yes:

* **Sensor simulation tick** — `SIMULATION_INTERVAL_SECONDS` in `.env`
  (Docker Compose path only).
* **Synthetic frequency** — `synthetic_period` in `terraform.tfvars`
  (default `EVERY_5_MINUTES`).
* **Error-injection probability** — `ERROR_RUN_PROBABILITY` in
  `terraform/synthetics.tf` (default `0.25` = ~25% of synthetic runs
  trip a 500). Lower it for a "happy path" demo, raise it to make the
  Errors Inbox light up faster.

### What's the cleanest way to reset between demos?

```bash
cd relifarm-lambda/terraform && terraform destroy
```

Then redeploy fresh when needed. Don't try to "pause" the stack — App
Runner doesn't have a stop-without-destroy mode, and you'd still be
billed for the NAT gateway and RDS while idle. See README → Teardown for
the full checklist.
