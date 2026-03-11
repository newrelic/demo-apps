#!/bin/bash

# ==============================================================================
# S3 Exporter Configuration Merge Script
# ==============================================================================
# This script merges the S3 exporter configuration with the existing
# Pipeline Control Gateway configuration.
#
# Usage:
#   ./scripts/merge-s3-config.sh
#
# What it does:
#   1. Exports current gateway config
#   2. Adds S3 exporter, debug exporter, and S3 pipelines
#   3. Creates backup of original config
#   4. Outputs merged config to /tmp/gateway-config-with-s3.yaml
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="newrelic"
CONFIGMAP_NAME="pipeline-control-gateway-config"
BACKUP_DIR="backups"
OUTPUT_FILE="/tmp/gateway-config-with-s3.yaml"

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}S3 Exporter Configuration Merge${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""

# ==============================================================================
# Step 1: Create backup directory
# ==============================================================================
echo -e "${YELLOW}Step 1: Creating backup directory...${NC}"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓ Backup directory ready${NC}"
echo ""

# ==============================================================================
# Step 2: Export current gateway configuration
# ==============================================================================
echo -e "${YELLOW}Step 2: Exporting current gateway configuration...${NC}"
kubectl get configmap "$CONFIGMAP_NAME" -n "$NAMESPACE" \
  -o jsonpath='{.data.deployment-config\.yaml}' > "$OUTPUT_FILE"

if [ ! -s "$OUTPUT_FILE" ]; then
  echo -e "${RED}✗ Failed to export configuration${NC}"
  exit 1
fi

echo -e "${GREEN}✓ Current config exported to $OUTPUT_FILE${NC}"

# Create timestamped backup
BACKUP_FILE="$BACKUP_DIR/gateway-config-backup-$(date +%Y%m%d-%H%M%S).yaml"
cp "$OUTPUT_FILE" "$BACKUP_FILE"
echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"
echo ""

# ==============================================================================
# Step 3: Check for existing S3 configuration
# ==============================================================================
echo -e "${YELLOW}Step 3: Checking for existing S3 configuration...${NC}"
if grep -q "awss3" "$OUTPUT_FILE"; then
  echo -e "${RED}⚠ WARNING: S3 exporter (awss3) already exists in configuration${NC}"
  echo -e "${RED}   This script will not modify an already-configured gateway.${NC}"
  echo -e "${RED}   If you need to update, please edit manually or restore from backup.${NC}"
  exit 1
fi
echo -e "${GREEN}✓ No existing S3 configuration found - safe to proceed${NC}"
echo ""

# ==============================================================================
# Step 4: Add S3 exporter configuration using Python
# ==============================================================================
echo -e "${YELLOW}Step 4: Merging S3 exporter configuration...${NC}"

python3 << 'PYTHON_SCRIPT'
import yaml
import sys

# Load current configuration
with open('/tmp/gateway-config-with-s3.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Ensure exporters section exists
if 'exporters' not in config:
    config['exporters'] = {}

# Add AWS S3 exporter
config['exporters']['awss3'] = {
    's3uploader': {
        'region': '${AWS_REGION}',
        's3_bucket': '${S3_BUCKET}',
        's3_prefix': 'telemetry',
        'compression': 'gzip',
        'role_arn': '${AWS_ROLE_ARN}'
    },
    'marshaler': 'otlp_json'
}

# Add debug exporter
config['exporters']['debug'] = {
    'verbosity': 'detailed',
    'sampling_initial': 5,
    'sampling_thereafter': 200
}

# Ensure service.pipelines section exists
if 'service' not in config:
    config['service'] = {}
if 'pipelines' not in config['service']:
    config['service']['pipelines'] = {}

# Add S3 compliance pipelines
config['service']['pipelines']['logs/s3-compliance'] = {
    'receivers': ['nrproprietaryreceiver', 'otlp/receiver'],
    'processors': ['probabilistic_sampler/Logs'],
    'exporters': ['awss3', 'debug']
}

config['service']['pipelines']['traces/s3-compliance'] = {
    'receivers': ['nrproprietaryreceiver', 'otlp/receiver'],
    'processors': [],
    'exporters': ['awss3', 'debug']
}

# Write updated configuration
with open('/tmp/gateway-config-with-s3.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120)

print("✓ S3 configuration merged successfully")

PYTHON_SCRIPT

if [ $? -ne 0 ]; then
  echo -e "${RED}✗ Failed to merge S3 configuration${NC}"
  echo -e "${RED}   You may need to install PyYAML: pip3 install pyyaml${NC}"
  exit 1
fi

echo -e "${GREEN}✓ S3 configuration merged${NC}"
echo ""

# ==============================================================================
# Step 5: Validate YAML syntax
# ==============================================================================
echo -e "${YELLOW}Step 5: Validating YAML syntax...${NC}"
python3 -c "import yaml; yaml.safe_load(open('$OUTPUT_FILE', 'r'))" 2>/dev/null
if [ $? -ne 0 ]; then
  echo -e "${RED}✗ YAML validation failed${NC}"
  echo -e "${RED}   The merged configuration has syntax errors.${NC}"
  echo -e "${RED}   Original config has been preserved in backup: $BACKUP_FILE${NC}"
  exit 1
fi
echo -e "${GREEN}✓ YAML syntax is valid${NC}"
echo ""

# ==============================================================================
# Summary
# ==============================================================================
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}Configuration Merge Complete!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "📄 Merged configuration: ${GREEN}$OUTPUT_FILE${NC}"
echo -e "💾 Backup location: ${GREEN}$BACKUP_FILE${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "1. Review the merged configuration:"
echo -e "   ${GREEN}less $OUTPUT_FILE${NC}"
echo ""
echo -e "2. Apply the updated ConfigMap:"
echo -e "   ${GREEN}kubectl create configmap $CONFIGMAP_NAME \\${NC}"
echo -e "   ${GREEN}  --from-file=deployment-config.yaml=$OUTPUT_FILE \\${NC}"
echo -e "   ${GREEN}  -n $NAMESPACE \\${NC}"
echo -e "   ${GREEN}  --dry-run=client -o yaml | kubectl apply -f -${NC}"
echo ""
echo -e "3. Restart gateway pods:"
echo -e "   ${GREEN}kubectl rollout restart deployment pipeline-control-gateway -n $NAMESPACE${NC}"
echo ""
echo -e "${YELLOW}To restore from backup if needed:${NC}"
echo -e "   ${GREEN}kubectl create configmap $CONFIGMAP_NAME \\${NC}"
echo -e "   ${GREEN}  --from-file=deployment-config.yaml=$BACKUP_FILE \\${NC}"
echo -e "   ${GREEN}  -n $NAMESPACE \\${NC}"
echo -e "   ${GREEN}  --dry-run=client -o yaml | kubectl apply -f -${NC}"
echo ""
