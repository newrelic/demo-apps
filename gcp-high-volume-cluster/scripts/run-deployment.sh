#!/bin/bash
set -e

# Setup environment
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"
export USE_GKE_GCLOUD_AUTH_PLUGIN=True

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo "Error: .env file not found"
    exit 1
fi

echo "========================================="
echo "Gateway Integration Deployment"
echo "========================================="
echo "Project: $GCP_PROJECT_ID"
echo "Started: $(date)"
echo ""

# Function to run step with logging
run_step() {
    local step_num=$1
    local step_name=$2
    echo ""
    echo "========================================="
    echo "Step $step_num: $step_name"
    echo "========================================="
}

# Step 3: Verify Current State
run_step 3 "Verify Current State"

echo "Gateway Pods:"
kubectl get pods -n newrelic -l app.kubernetes.io/name=pipeline-control-gateway || echo "No gateway pods found"

echo ""
echo "nri-bundle Release:"
helm list -n newrelic || echo "No helm releases found"

echo ""
echo "Current Instrumentation CRD:"
kubectl get instrumentation -n prod 2>&1 || echo "No instrumentation found"

echo ""
echo "Application Deployments:"
kubectl get deployments -n prod | head -10

# Step 4: Backup Current Configuration
run_step 4 "Backup Current Configuration"

mkdir -p backups
timestamp=$(date +%Y%m%d-%H%M%S)

echo "Creating backups..."
helm get values nri-bundle -n newrelic > backups/nri-bundle-backup-${timestamp}.yaml 2>&1 || echo "Could not backup nri-bundle"
kubectl get instrumentation newrelic-instrumentation -n prod -o yaml > backups/instrumentation-backup-${timestamp}.yaml 2>/dev/null || echo "No existing Instrumentation CRD to backup"
kubectl get configmap pipeline-control-gateway-config -n newrelic -o yaml > backups/gateway-config-backup-${timestamp}.yaml 2>&1 || echo "Could not backup gateway config"

echo "Backups saved to backups/"
ls -lh backups/*${timestamp}* 2>/dev/null || echo "No backups created"

# Step 5: Upgrade nri-bundle
run_step 5 "Upgrade nri-bundle with Gateway Configuration"

echo "Upgrading nri-bundle..."
helm upgrade nri-bundle newrelic/nri-bundle \
  --namespace newrelic \
  --reuse-values \
  -f k8s/nri-bundle-values.yaml \
  --set global.licenseKey=$NEW_RELIC_LICENSE_KEY

echo ""
echo "Waiting for infrastructure rollout..."
kubectl rollout status daemonset/nri-bundle-newrelic-infrastructure -n newrelic --timeout=300s || echo "Rollout status check failed"

# Step 6: Update Instrumentation CRD
run_step 6 "Update Instrumentation CRD"

echo "Applying Instrumentation CRD..."
kubectl apply -f k8s/instrumentation.yaml

echo ""
echo "Verifying OTLP configuration..."
kubectl get instrumentation newrelic-instrumentation -n prod -o yaml | grep -A 3 "OTEL_EXPORTER_OTLP_ENDPOINT"

# Step 7: Restart Applications
run_step 7 "Restart Applications"

echo "Restarting all deployments in prod namespace..."
kubectl rollout restart deployment -n prod

echo ""
echo "Waiting for rollout to complete (this may take a few minutes)..."
kubectl rollout status deployment -n prod --timeout=600s || echo "Some deployments may still be rolling out"

# Step 8: Run Verification
run_step 8 "Run Verification Script"

if [ -x ./scripts/verify-gateway-integration.sh ]; then
    ./scripts/verify-gateway-integration.sh
else
    echo "Verification script not executable, running with bash..."
    bash ./scripts/verify-gateway-integration.sh
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo "Completed: $(date)"
echo ""
echo "Next steps:"
echo "1. Check gateway metrics: kubectl port-forward -n newrelic svc/pipeline-control-gateway 8888:8888"
echo "2. Update gateway drop rules: ./scripts/update-gateway-filter.sh"
echo "3. Verify data in New Relic APM"
echo ""
