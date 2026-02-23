#!/bin/bash
set -e

PROJECT_ID=${GCP_PROJECT_ID}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: GCP_PROJECT_ID environment variable is not set"
  exit 1
fi

echo "Building and pushing images to GCR..."

# Build single hello world image
echo "Building hello-world app..."
docker build -t gcr.io/$PROJECT_ID/hello-world:latest app/
echo "Pushing hello-world to GCR..."
docker push gcr.io/$PROJECT_ID/hello-world:latest

# Build loadgen
echo "Building loadgen..."
docker build -t gcr.io/$PROJECT_ID/loadgen:latest k8s/loadgen/
echo "Pushing loadgen to GCR..."
docker push gcr.io/$PROJECT_ID/loadgen:latest

echo "Done! Images pushed to GCR:"
echo "  - gcr.io/$PROJECT_ID/hello-world:latest"
echo "  - gcr.io/$PROJECT_ID/loadgen:latest"
