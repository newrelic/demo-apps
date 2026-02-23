#!/bin/bash
# Generates k8s/apps.yaml with N app deployments
# Usage: ./generate-apps.sh 12 <project-id>

NUM_APPS=${1:-12}
PROJECT_ID=${2:-$GCP_PROJECT_ID}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID not provided and GCP_PROJECT_ID not set"
  exit 1
fi

echo "Generating $NUM_APPS app deployments..."

> k8s/apps.yaml
for i in $(seq 1 $NUM_APPS); do
  cat k8s/app-template.yaml | sed "s/{{NUM}}/$i/g" | sed "s/{{PROJECT_ID}}/$PROJECT_ID/g" >> k8s/apps.yaml
  echo "---" >> k8s/apps.yaml
done

echo "Generated k8s/apps.yaml with $NUM_APPS apps"
