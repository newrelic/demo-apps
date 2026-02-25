# GCP High Volume Cluster Setup Guide

This document captures all commands and steps used to set up the GKE cluster.

**Note**: All commands assume you're running them from the project root directory unless otherwise specified.

## Prerequisites

- Google Cloud SDK installed
- Terraform installed
- kubectl installed
- Docker installed (for building images)

## 1. Service Account Setup

### Service Account Setup

1. **Create or use existing service account** in your GCP project with necessary permissions
2. **Add credentials to .env file**:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your service account details:
# - GCP_PROJECT_ID
# - GCP_SERVICE_ACCOUNT_EMAIL
# - GCP_SERVICE_ACCOUNT_KEY_ID
# - GCP_SERVICE_ACCOUNT_PRIVATE_KEY
# - GCP_SERVICE_ACCOUNT_CLIENT_ID
```

3. **Generate the service account key file**:

```bash
source .env
./scripts/generate-service-account-key.sh
```

This creates `service-account-key.json` from your .env variables (already in `.gitignore`).

### Grant IAM Permissions

Grant necessary roles to the service account:

```bash
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:$PATH

# Load your environment variables
source .env

# Grant Container Admin role (for GKE management)
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$GCP_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/container.admin"

# Grant Service Account User role
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$GCP_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# Grant Compute Network Admin role
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$GCP_SERVICE_ACCOUNT_EMAIL" \
  --role="roles/compute.networkAdmin"
```

## 2. Enable Required APIs

```bash
# Load environment variables
source .env

# Enable Compute Engine API
gcloud services enable compute.googleapis.com --project=$GCP_PROJECT_ID

# Enable Container API (GKE)
gcloud services enable container.googleapis.com --project=$GCP_PROJECT_ID
```

## 3. Terraform Configuration

### Save Service Account Key

Save the service account JSON key to:
```
terraform/service-account-key.json
```

**Important:** This file is in `.gitignore` and should never be committed!

### Terraform Files Structure

```
terraform/
├── main.tf                    # Main infrastructure configuration
├── variables.tf               # Variable definitions
├── terraform.tfvars          # Variable values (gitignored)
└── service-account-key.json  # Service account credentials (gitignored)
```

### Key Infrastructure Components

The Terraform configuration creates:

1. **VPC Network** (`gke-network`)
   - Custom network without auto-created subnetworks

2. **Subnet** (`gke-subnet`)
   - Primary CIDR: 10.0.0.0/24
   - Pod range: 10.1.0.0/16
   - Service range: 10.2.0.0/16
   - Private Google Access enabled

3. **Cloud Router & NAT**
   - Router: `gke-router`
   - NAT: `gke-nat`
   - Provides internet access for private nodes

4. **GKE Cluster** (`gcp-high-volume-cluster`)
   - Region: us-west1
   - Private nodes (no external IPs)
   - Public endpoint for kubectl access
   - Workload Identity enabled

5. **Node Pool** (`primary-pool`)
   - Machine type: n1-standard-4
   - Disk: 100GB per node
   - Initial nodes: 3
   - Autoscaling: 3-20 nodes

## 4. Deploy Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan the deployment
terraform plan

# Apply the configuration
terraform apply -auto-approve
```

**Note:** Cluster creation takes approximately 10-15 minutes.

## 5. Configure kubectl Access

### Install GKE Auth Plugin

```bash
export PATH=/opt/homebrew/share/google-cloud-sdk/bin:$PATH
gcloud components install gke-gcloud-auth-plugin
```

### Make Environment Changes Persistent

Add these lines to your `~/.zshrc` (or `~/.bashrc` for bash):

```bash
# Google Cloud SDK PATH
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

# Enable GKE Auth Plugin
export USE_GKE_GCLOUD_AUTH_PLUGIN=True

# Optional: Enable shell completion
if [ -f '/opt/homebrew/share/google-cloud-sdk/completion.zsh.inc' ]; then
  source '/opt/homebrew/share/google-cloud-sdk/completion.zsh.inc'
fi
if [ -f '/opt/homebrew/share/google-cloud-sdk/path.zsh.inc' ]; then
  source '/opt/homebrew/share/google-cloud-sdk/path.zsh.inc'
fi
```

Then reload your shell:
```bash
source ~/.zshrc
```

### Update kubeconfig

```bash
source .env
gcloud container clusters get-credentials gcp-high-volume-cluster \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID
```

### Verify Connection

```bash
kubectl get nodes
kubectl cluster-info
```

## 6. Build and Push Container Images

### Configure Docker for GCR/Artifact Registry

```bash
# Authenticate Docker with GCP
gcloud auth configure-docker
```

### Build Application Images

```bash
# Load environment variables
source .env

# Build the main application
cd app
docker build -t gcr.io/$GCP_PROJECT_ID/gcp-app:latest .

# Push to GCR
docker push gcr.io/$GCP_PROJECT_ID/gcp-app:latest
```

### Build Load Generator (if applicable)

```bash
# Build load generator
cd loadgen
docker build -t gcr.io/$GCP_PROJECT_ID/loadgen:latest .

# Push to GCR
docker push gcr.io/$GCP_PROJECT_ID/loadgen:latest
```

## 7. Deploy Applications to GKE

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get services
```

## Infrastructure Details

### Network Configuration
- **VPC**: gke-network (custom mode)
- **Subnet**: gke-subnet (10.0.0.0/24)
- **Pod IPs**: 10.1.0.0/16
- **Service IPs**: 10.2.0.0/16

### Security Features
- Private GKE nodes (no external IPs)
- Cloud NAT for outbound internet access
- Organizational policy compliance (external IP restrictions)
- Workload Identity for secure pod authentication

### Cluster Configuration
- **Name**: gcp-high-volume-cluster
- **Region**: us-west1 (multi-zone)
- **Zones**: us-west1-a, us-west1-b, us-west1-c
- **Deletion Protection**: Disabled

## Common Commands

### Check Cluster Status
```bash
source .env
gcloud container clusters list --project=$GCP_PROJECT_ID
gcloud container clusters describe gcp-high-volume-cluster --region=$GCP_REGION --project=$GCP_PROJECT_ID
```

### Scale Node Pool
```bash
gcloud container clusters update gcp-high-volume-cluster \
  --region=us-west1 \
  --enable-autoscaling \
  --min-nodes=3 \
  --max-nodes=30 \
  --node-pool=primary-pool
```

### View Logs
```bash
kubectl logs -f deployment/<deployment-name>
gcloud logging read "resource.type=k8s_cluster AND resource.labels.cluster_name=gcp-high-volume-cluster" --limit 50
```

### Clean Up Resources
```bash
cd terraform
terraform destroy -auto-approve
```

## Current Status (Last Updated: 2026-02-25)

✅ **Google Cloud SDK**: Installed and configured (v558.0.0)
✅ **GKE Auth Plugin**: Installed (v0.5.12)
✅ **Service Account**: Configured via .env file
✅ **Cluster**: Running with 9 nodes
✅ **gcloud access**: Working
✅ **kubectl access**: Working (DNS endpoint + Cloudflare Gateway exclusion)

### One-Time Setup: Configure Your Shell

Add these environment variables to your `~/.zshrc` (or `~/.bashrc` for bash):

```bash
cat >> ~/.zshrc << 'EOF'

# Google Cloud SDK
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
export USE_GKE_GCLOUD_AUTH_PLUGIN=True

# Optional: Enable shell completion
if [ -f '/opt/homebrew/share/google-cloud-sdk/completion.zsh.inc' ]; then
  source '/opt/homebrew/share/google-cloud-sdk/completion.zsh.inc'
fi
if [ -f '/opt/homebrew/share/google-cloud-sdk/path.zsh.inc' ]; then
  source '/opt/homebrew/share/google-cloud-sdk/path.zsh.inc'
fi
EOF
```

Then reload your shell:
```bash
source ~/.zshrc
```

### Quick Connect Commands

After the one-time setup above, these commands will work in any new terminal:

```bash
# Load environment variables (run from project root)
source .env

# Generate service account key file (if not already done)
./scripts/generate-service-account-key.sh

# Authenticate with service account
gcloud auth activate-service-account $GCP_SERVICE_ACCOUNT_EMAIL \
  --key-file=./service-account-key.json \
  --project=$GCP_PROJECT_ID

# Get cluster credentials
gcloud container clusters get-credentials gcp-high-volume-cluster \
  --region $GCP_REGION \
  --project $GCP_PROJECT_ID

# Test connection
kubectl get nodes
kubectl get pods -n prod
```

## Troubleshooting

### Certificate Verification Error (RESOLVED)

**Symptom**: `kubectl` commands fail with:
```
tls: failed to verify certificate: x509: certificate signed by unknown authority
```

**Root Cause**: Cloudflare WARP was performing TLS inspection on `*.gke.goog` domains, presenting Cloudflare's certificate instead of Google's.

**Solution (Working)**:

**Step 1: Enable DNS-based control plane access**
```bash
source .env
gcloud container clusters update gcp-high-volume-cluster \
  --region $GCP_REGION \
  --project $GCP_PROJECT_ID \
  --enable-dns-access
```

**Step 2: Have IT exclude `*.gke.goog` from TLS inspection in Cloudflare Gateway**
- Request IT to exclude (not just allowlist) the domain from TLS decryption
- This allows Google's certificate to be presented directly to kubectl
- Verify with: `echo | openssl s_client -connect <dns-endpoint>:443 -showcerts 2>/dev/null | openssl x509 -noout -issuer`
- Should show: `issuer=C=US, O=Google Trust Services, CN=WR2`

**Step 3: Remove cluster CA cert from kubeconfig**
```bash
# Get your cluster context name
CLUSTER_CONTEXT=$(kubectl config current-context)

# Remove the embedded CA certificate
kubectl config unset clusters.$CLUSTER_CONTEXT.certificate-authority-data

# Get the DNS endpoint from gcloud
DNS_ENDPOINT=$(gcloud container clusters describe gcp-high-volume-cluster \
  --region $GCP_REGION --project $GCP_PROJECT_ID \
  --format="value(controlPlaneEndpointsConfig.dnsEndpointConfig.endpoint)")

# Update kubeconfig to use DNS endpoint
kubectl config set-cluster $CLUSTER_CONTEXT \
  --server=https://$DNS_ENDPOINT
```

**Step 4: Test kubectl**
```bash
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
kubectl get pods --all-namespaces
```

### Can't Access Cluster
```bash
# Re-authenticate with service account (run from project root)
source .env
gcloud auth activate-service-account $GCP_SERVICE_ACCOUNT_EMAIL \
  --key-file=./service-account-key.json \
  --project=$GCP_PROJECT_ID

# Update kubeconfig
gcloud container clusters get-credentials gcp-high-volume-cluster \
  --region=$GCP_REGION \
  --project=$GCP_PROJECT_ID

# Check auth plugin
which gke-gcloud-auth-plugin
# Should output: /opt/homebrew/share/google-cloud-sdk/bin/gke-gcloud-auth-plugin
```

### Nodes Not Starting
- Check organizational policies for external IP restrictions
- Verify Cloud NAT is properly configured
- Check IAM permissions for service account

### Terraform Errors
```bash
source .env

# Refresh state
terraform refresh

# Import existing resources if needed
terraform import google_container_cluster.primary \
  projects/$GCP_PROJECT_ID/locations/$GCP_REGION/clusters/gcp-high-volume-cluster
```

## Next Steps

1. Build and push container images to GCR
2. Deploy applications using Kubernetes manifests
3. Configure monitoring and logging
4. Set up CI/CD pipelines
5. Configure autoscaling policies
6. Set up ingress/load balancing

## Resources

- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [kubectl Cheat Sheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
