# GCP High-Volume Cluster Demo

**Purpose:** Production-scale GKE cluster generating high volumes of MELT (Metrics, Events, Logs, Traces) data for Gartner demos and sales enablement.

## Overview

A scalable GKE deployment with a simple Java "Hello World" application deployed multiple times with independent load generators. Each app instance is instrumented with New Relic via nri-bundle's auto-attach APM.

### Goals
- **Volume:** Generate 2+ GB of telemetry data per day to New Relic
- **Scale:** Demonstrate production-level traffic patterns
- **Simplicity:** Single hello world Java app, duplicated N times for volume
- **Flexibility:** Independent traffic control per app instance via dedicated Locust load generators
- **Instrumentation:** Zero-code New Relic APM via k8s-agent-operator auto-attach

## Architecture

### Simple Hello World App, Deployed Many Times

**Single App:**
- Basic Java HTTP server with `/hello` endpoint
- Returns "Hello from app-N!"
- Minimal dependencies (just JDK)
- Instrumented via New Relic auto-attach (no manual agent setup)

**Deployed N Times:**
- `app-1`, `app-2`, `app-3`, ... `app-N` (default: 12)
- Each uses the **same Docker image**
- Only difference: `SERVICE_NAME` environment variable
- Each has 5 replicas (60 total pods initially)

**Independent Load Generators:**
- One Locust deployment per app instance
- `loadgen-1` → `app-1`, `loadgen-2` → `app-2`, etc.
- Each loadgen has independently configurable `USERS` count
- Allows fine-grained traffic control per app

**Example Traffic Configuration:**
```
app-1 (5 replicas) ← loadgen-1 (500 users) ← HIGH TRAFFIC
app-2 (5 replicas) ← loadgen-2 (200 users) ← MEDIUM TRAFFIC
app-3 (5 replicas) ← loadgen-3 (50 users)  ← LOW TRAFFIC
...
```

### Infrastructure

- **Platform:** Google Kubernetes Engine (GKE)
- **Namespaces:**
  - `dev` - Development environment
  - `staging` - Staging environment
  - `prod` - Production environment (highest load)
- **Instrumentation:**
  - **Infrastructure:** nri-bundle (DaemonSet for K8s metrics)
  - **APM:** nri-bundle auto-attach (automatic Java agent injection)
- **Scaling:**
  - Horizontal Pod Autoscaler (HPA) based on CPU/memory
  - Configurable min/max replicas per service
  - Node auto-scaling via GKE

## Project Structure

```
gcp-high-volume-cluster/
├── README.md                    # This file
├── apps/                        # Java microservices source code
│   ├── api-gateway/
│   ├── user-service/
│   ├── order-service/
│   ├── payment-service/
│   ├── inventory-service/
│   ├── notification-service/
│   ├── analytics-service/
│   ├── search-service/
│   ├── recommendation-service/
│   ├── reporting-service/
│   ├── audit-service/
│   └── health-check-service/
├── k8s/                         # Kubernetes manifests
│   ├── base/                    # Base configs (Kustomize)
│   ├── overlays/
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── nri-bundle/              # New Relic instrumentation
├── terraform/                   # GCP infrastructure as code
│   ├── gke-cluster.tf
│   ├── networking.tf
│   └── variables.tf
├── scripts/                     # Automation scripts
│   ├── build-and-push.sh        # Build & push all images to GCR
│   ├── create-namespace.sh      # Create new environment namespace
│   ├── deploy.sh                # Deploy to specific environment
│   └── scale.sh                 # Scale deployments
├── load-testing/                # Traffic generation
│   ├── locustfile.py            # Locust load test scenarios
│   └── synthetic-scripts/       # New Relic synthetic monitors
└── docs/                        # Documentation
    ├── deployment.md
    ├── monitoring.md
    └── troubleshooting.md
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Create base Java Spring Boot service template
- [ ] Set up GCP project and GKE cluster (Terraform)
- [ ] Configure GCR/Artifact Registry
- [ ] Implement build and push automation
- [ ] Create base Kubernetes manifests

### Phase 2: Service Development (Week 1-2)
- [ ] Generate 12 microservices from template
- [ ] Implement different response characteristics per service
- [ ] Add service-to-service communication patterns
- [ ] Add configurable error injection
- [ ] Add structured logging (JSON format)

### Phase 3: Instrumentation (Week 2)
- [ ] Deploy nri-bundle to cluster
- [ ] Configure auto-attach for Java APM
- [ ] Verify telemetry flow to New Relic
- [ ] Configure custom attributes per service
- [ ] Set up New Relic alerts and dashboards

### Phase 4: Multi-Environment (Week 2-3)
- [ ] Create namespace automation scripts
- [ ] Deploy to dev/staging/prod namespaces
- [ ] Configure different scaling parameters per env
- [ ] Verify namespace isolation in New Relic

### Phase 5: Traffic Generation (Week 3)
- [ ] Create Locust load testing scripts
- [ ] Deploy traffic generator pods in cluster
- [ ] Configure realistic traffic patterns
- [ ] Implement peak hour multipliers
- [ ] Verify target data volume (2+ GB/day)

### Phase 6: Optimization & Documentation (Week 3-4)
- [ ] Optimize for cost (right-size pods)
- [ ] Add runbooks and troubleshooting guides
- [ ] Create demo walkthrough documentation
- [ ] Performance testing and tuning
- [ ] Final validation with Gartner use cases

## Quick Start

### Prerequisites
- GCP account with billing enabled
- `gcloud` CLI installed and authenticated
- `kubectl` installed
- `terraform` installed (for GKE cluster creation)
- `docker` CLI authenticated to GCR
- New Relic license key

### 1. Set Up Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your values
export GCP_PROJECT_ID="your-gcp-project-id"
export NEW_RELIC_LICENSE_KEY="your-license-key"
export NEW_RELIC_ACCOUNT_ID="6321322"

# Load environment variables
source .env

# Authenticate with GCP
gcloud auth login
gcloud config set project $GCP_PROJECT_ID

# Configure Docker for GCR
gcloud auth configure-docker gcr.io
```

### 2. Create GKE Cluster

```bash
cd terraform

# Copy and edit tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id

# Create cluster
terraform init
terraform apply

# Get cluster credentials
gcloud container clusters get-credentials gcp-high-volume-cluster --region us-west1
```

### 3. Build and Push Images

```bash
cd ..
./scripts/build-and-push.sh
```

This builds and pushes:
- `gcr.io/PROJECT_ID/hello-world:latest` - Java app
- `gcr.io/PROJECT_ID/loadgen:latest` - Locust load generator

### 4. Deploy Everything

```bash
./scripts/deploy-all.sh
```

This will:
1. Generate Kubernetes manifests for 12 apps + 12 loadgens
2. Deploy nri-bundle with auto-attach enabled
3. Create prod namespace and secrets
4. Deploy all apps and loadgens

### 5. Verify Deployment

```bash
# Check app pods
kubectl get pods -n prod

# Check New Relic pods
kubectl get pods -n newrelic

# View logs from an app
kubectl logs -n prod -l app=app-1 -f

# View logs from a loadgen
kubectl logs -n prod -l app=loadgen-1 -f
```

### 6. View in New Relic

Navigate to New Relic account **6321322** and look for:
- **APM:** "GCP High Volume - App 1", "GCP High Volume - App 2", etc.
- **Infrastructure:** Kubernetes cluster "gcp-high-volume-cluster"
- **Logs:** Application logs from all pods

## Monitoring

### New Relic Dashboards
- **Cluster Overview:** Infrastructure metrics, node health
- **Service Map:** Distributed tracing across all services
- **Error Analysis:** Error rates, types, stack traces
- **Performance:** Response times, throughput, apdex

### Key Metrics
- **Throughput:** ~9.5M requests/day
- **Trace volume:** ~200-300k spans/day
- **Log volume:** ~1-2 GB/day
- **Metric volume:** ~500MB/day

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | GCP project ID | `my-gcp-project` |
| `GCP_REGION` | GCP region | `us-west1` |
| `NEW_RELIC_LICENSE_KEY` | New Relic license key | `NRAK-...` |
| `NEW_RELIC_ACCOUNT_ID` | New Relic account ID | `6321322` |

### Scaling Traffic

**Scale traffic for a specific app:**

```bash
# Set app-1 to 500 concurrent users
./scripts/scale-traffic.sh 1 500

# Set app-3 to 50 concurrent users (low traffic)
./scripts/scale-traffic.sh 3 50
```

**Scale app replicas:**

```bash
# Scale app-1 to 10 replicas for more capacity
kubectl scale deployment app-1 -n prod --replicas=10
```

**Add more apps:**

```bash
# Generate 20 apps instead of 12
./scripts/generate-apps.sh 20
./scripts/generate-loadgens.sh 20

# Apply
kubectl apply -f k8s/apps.yaml
kubectl apply -f k8s/loadgens.yaml
```

### Increasing Data Volume

To generate more telemetry data:

1. **Increase Locust users across all loadgens:**
   ```bash
   for i in {1..12}; do
     kubectl set env deployment/loadgen-$i -n prod USERS=500
   done
   ```

2. **Scale up app replicas:**
   ```bash
   for i in {1..12}; do
     kubectl scale deployment app-$i -n prod --replicas=10
   done
   ```

3. **Add more app instances:**
   ```bash
   ./scripts/generate-apps.sh 24
   ./scripts/generate-loadgens.sh 24
   kubectl apply -f k8s/apps.yaml
   kubectl apply -f k8s/loadgens.yaml
   ```

## Cost Estimation

**Monthly GCP costs (estimated):**
- GKE cluster (3 nodes, n1-standard-4): ~$250/month
- Load balancer: ~$20/month
- Container Registry storage: ~$10/month
- Network egress: ~$50/month
- **Total:** ~$330/month

**New Relic data ingest (estimated):**
- 2GB telemetry/day × 30 days = 60GB/month
- Cost depends on New Relic plan

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md) for common issues and solutions.

## Contributing

This is an internal demo application. See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

## Questions to Answer

Before proceeding with implementation, please clarify:

1. **Data volume:** Is "couple gigs per day" referring to total MELT data sent to New Relic, or just traces?
2. **App communication:** Should services call each other (microservices mesh) or be independent?
3. **Velocity definition:** Should different velocities mean different request rates, latencies, or both?
4. **GCP details:** Which project, region, and should we use GKE Autopilot or Standard?
5. **Registry:** GCR or Artifact Registry?
6. **Namespaces:** How many environments initially? (dev, staging, prod, or more?)
7. **Traffic generation:** Include built-in load generators or use external tools?
8. **Error injection:** Should apps generate realistic error rates?
9. **New Relic config:** Specific account ID? All namespaces to same app or separate?

## License

Internal use only.
