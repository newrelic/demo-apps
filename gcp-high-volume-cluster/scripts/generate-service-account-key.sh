#!/bin/bash
set -e

# Generate service-account-key.json from environment variables
# Usage: ./scripts/generate-service-account-key.sh

# Check if required environment variables are set
if [ -z "$GCP_PROJECT_ID" ] || [ -z "$GCP_SERVICE_ACCOUNT_EMAIL" ] || [ -z "$GCP_SERVICE_ACCOUNT_PRIVATE_KEY" ]; then
    echo "Error: Required environment variables not set."
    echo "Please source your .env file first:"
    echo "  source .env"
    echo ""
    echo "Required variables:"
    echo "  - GCP_PROJECT_ID"
    echo "  - GCP_SERVICE_ACCOUNT_EMAIL"
    echo "  - GCP_SERVICE_ACCOUNT_KEY_ID"
    echo "  - GCP_SERVICE_ACCOUNT_PRIVATE_KEY"
    echo "  - GCP_SERVICE_ACCOUNT_CLIENT_ID"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Use Python to generate the JSON file with proper escaping
python3 << 'PYTHON_SCRIPT'
import json
import os

data = {
    "type": "service_account",
    "project_id": os.environ["GCP_PROJECT_ID"],
    "private_key_id": os.environ["GCP_SERVICE_ACCOUNT_KEY_ID"],
    "private_key": os.environ["GCP_SERVICE_ACCOUNT_PRIVATE_KEY"],
    "client_email": os.environ["GCP_SERVICE_ACCOUNT_EMAIL"],
    "client_id": os.environ["GCP_SERVICE_ACCOUNT_CLIENT_ID"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.environ['GCP_SERVICE_ACCOUNT_EMAIL']}",
    "universe_domain": "googleapis.com"
}

with open(f"{os.environ.get('PROJECT_ROOT', '.')}/service-account-key.json", "w") as f:
    json.dump(data, f, indent=2)
PYTHON_SCRIPT

echo "✓ Generated service-account-key.json"
echo "  Location: $PROJECT_ROOT/service-account-key.json"
echo ""
echo "Note: This file is in .gitignore and should never be committed to git."
