# Glossary

Quick definitions for the AWS / NR / IaC terms that show up across this
repo's docs and Terraform code. Aimed at engineers comfortable in cloud
generally but not necessarily fluent in every AWS service used here.

---

**ACM (AWS Certificate Manager)**
Issues and renews TLS certificates for AWS-managed endpoints. Used here for
the dashboard custom domain (cert in `us-east-1` for CloudFront) and the
API custom domain (cert in your deployment region for API Gateway).

**API Gateway HTTP API**
The lightweight v2 API Gateway product (vs. the older REST API). Fronts
the two Lambdas and exposes `/yield-forecast` and `/valve-schedule`.

**App Runner**
AWS's managed container-running service. Pulls our core-engine image from
ECR, provides HTTPS automatically, and scales to zero between requests.
Available only in select regions — see Prerequisites.

**Browser Agent (NR)**
A JavaScript snippet that NR injects into the dashboard page. Captures
real-user telemetry (page loads, AJAX calls, errors) and — crucially for
this demo — auto-injects W3C Trace Context headers on every `fetch()` so
traces can connect Browser → Lambda → core-engine → Postgres.

**CloudFront**
AWS's CDN. Fronts the private S3 bucket holding the dashboard so users
get HTTPS automatically without needing a custom domain.

**Distributed Tracing (DT)**
The NR feature that stitches spans from multiple services into a single
end-to-end trace. ReliFarm shows DT across four hops.

**ECR (Elastic Container Registry)**
AWS's private Docker registry. We push the core-engine image here so App
Runner can pull it.

**ENI (Elastic Network Interface)**
A virtual NIC inside a VPC. App Runner's VPC connector creates ENIs in
your subnets so the App Runner workload can talk to private resources
like RDS — but the ENIs don't get public IPs, which is why we need the
NAT gateway for outbound internet egress.

**IAM (Identity and Access Management)**
AWS's permission system. The Lambdas and App Runner each have IAM roles
with the minimum permissions they need (read secrets, push logs, etc.).

**License key (NR)**
Also called "ingest key." This is what NR-instrumented apps use to *send*
telemetry. Format: 40 chars ending in `NRAL`. Distinct from the User API key.

**NAT Gateway**
AWS-managed Network Address Translation. Lets resources in private subnets
reach the internet without being publicly addressable themselves. We use
one to give App Runner ENIs outbound access to NR's data collector.

**OAC (Origin Access Control)**
The CloudFront feature that lets a CloudFront distribution authenticate to
a private S3 bucket so the bucket itself can stay non-public. Replaces the
older OAI (Origin Access Identity).

**RDS (Relational Database Service)**
AWS-managed Postgres/MySQL/etc. We use Postgres on `db.t4g.micro` by default.

**SCP (Service Control Policy)**
An AWS Organizations-level policy that overrides any IAM grant in member
accounts. Common SCPs in enterprise accounts deny `rds:CreateDBInstance`
(triggering our EC2 Postgres fallback) or cross-account
`lambda:GetLayerVersion` (triggering our local-bundle Lambda layer mode).

**Secrets Manager**
AWS-managed secret storage with rotation. We store the RDS master password
here so it never lives in Terraform state.

**SSM (Systems Manager) Session Manager**
The AWS service for interactive shell access to EC2 instances without
opening SSH ports or managing keys. Used to debug the EC2 Postgres
instance when `use_ec2_postgres = true`.

**Synthetic Monitor**
A scripted browser run NR executes from its own infrastructure on a
schedule, simulating a real user. ReliFarm provisions one that exercises
the full irrigation flow ~every 5 min and intentionally trips a 500 on
~25% of runs to populate the Errors Inbox and synthetic failure list.

**Terraform**
HashiCorp's IaC tool. Declarative `.tf` files describe AWS resources;
`terraform apply` reconciles real-world state with the declaration.

**User API key (NR)**
Format: starts with `NRAK-`. Used by automation (like our Terraform code)
to *create* NR resources via NR's API — Browser apps, Synthetic monitors,
etc. Distinct from the license key.

**VPC connector (App Runner)**
The App Runner feature that lets the App Runner service reach resources
inside your VPC (like RDS). Setting `egress_type = "VPC"` routes *all*
outbound traffic through it, which is why we need the NAT gateway for
NR's data collector.

**W3C Trace Context**
The web standard for trace propagation: `traceparent`, `tracestate`, and
`baggage` HTTP headers. NR auto-handles this on Browser, Lambda, and the
Python agent, but we also explicitly inject headers in the Lambda code
(`insert_distributed_trace_headers`) belt-and-suspenders.
