#!/bin/bash
set -e

if [ -z "$NEW_RELIC_LICENSE_KEY" ]; then
  echo "Error: NEW_RELIC_LICENSE_KEY environment variable is not set"
  exit 1
fi

if [ -z "$GCP_PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  exit 1
fi

# Generate manifests
echo "Generating Kubernetes manifests..."
./scripts/generate-apps.sh 12
./scripts/generate-loadgens.sh 12

# Deploy New Relic
echo "Deploying nri-bundle..."
helm repo add newrelic https://helm-charts.newrelic.com || true
helm repo update
helm upgrade --install nri-bundle newrelic/nri-bundle \
  --namespace newrelic --create-namespace \
  -f k8s/nri-bundle-values.yaml \
  --set global.licenseKey=$NEW_RELIC_LICENSE_KEY

# Create namespace and secret
echo "Creating namespace and secrets..."
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic newrelic-license \
  --from-literal=license-key=$NEW_RELIC_LICENSE_KEY \
  -n prod \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy apps and loadgens
echo "Deploying applications..."
kubectl apply -f k8s/apps.yaml

echo "Deploying load generators..."
kubectl apply -f k8s/loadgens.yaml

echo ""
echo "Deployment complete!"
echo ""
echo "To check status:"
echo "  kubectl get pods -n prod"
echo "  kubectl get pods -n newrelic"
echo ""
echo "To scale traffic for an app:"
echo "  ./scripts/scale-traffic.sh <app-number> <users>"
