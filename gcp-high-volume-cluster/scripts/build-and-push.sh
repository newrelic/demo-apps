#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID}
REGION=${GCP_REGION:-us-west1}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  exit 1
fi

echo "Building and pushing images to Artifact Registry ($REGION)..."
echo "NOTE: Building for linux/amd64 platform (GKE nodes)"

# Build single hello world image for AMD64
echo "Building hello-world app..."
docker buildx build --platform linux/amd64 \
  -t $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/hello-world:latest \
  --push \
  app/

# Build loadgen for AMD64
echo "Building loadgen..."
docker buildx build --platform linux/amd64 \
  -t $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/loadgen:latest \
  --push \
  k8s/loadgen/

echo "Done! Images pushed to Artifact Registry:"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/hello-world:latest"
echo "  - $REGION-docker.pkg.dev/$PROJECT_ID/demo-apps/loadgen:latest"
