#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-us-west1}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  exit 1
fi

echo "Building and pushing images to GCR ($REGION)..."

# Build single hello world image
echo "Building hello-world app..."
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/hello-world:latest app/
echo "Pushing hello-world to Artifact Registry..."
docker push $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/hello-world:latest

# Build loadgen
echo "Building loadgen..."
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/loadgen:latest k8s/loadgen/
echo "Pushing loadgen to Artifact Registry..."
docker push $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/loadgen:latest

echo "Done! Images pushed to Artifact Registry:"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/hello-world:latest"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/loadgen:latest"
