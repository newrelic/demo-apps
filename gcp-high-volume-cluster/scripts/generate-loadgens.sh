#!/bin/bash
# Generates k8s/loadgens.yaml with N loadgen deployments
# Usage: ./generate-loadgens.sh 12 <project-id> <default-users>

NUM_APPS=${1:-12}
PROJECT_ID=${2:-$GCP_PROJECT_ID}
DEFAULT_USERS=${3:-100}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID not provided and GCP_PROJECT_ID not set"
  exit 1
fi

echo "Generating $NUM_APPS loadgen deployments with $DEFAULT_USERS default users..."

> k8s/loadgens.yaml
for i in $(seq 1 $NUM_APPS); do
  cat k8s/loadgen-template.yaml | \
    sed "s/{{NUM}}/$i/g" | \
    sed "s/{{PROJECT_ID}}/$PROJECT_ID/g" | \
    sed "s/{{USERS}}/$DEFAULT_USERS/g" >> k8s/loadgens.yaml
  echo "---" >> k8s/loadgens.yaml
done

echo "Generated k8s/loadgens.yaml with $NUM_APPS loadgens"
