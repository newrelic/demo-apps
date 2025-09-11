#!/bin/bash
set -e

# --- Configuration ---
# Package names for the Lambda function and the New Relic layer
FUNCTION_PACKAGE_NAME="lambda_package.zip"
LAYER_PACKAGE_NAME="newrelic-layer.zip"
REGION=${AWS_REGION:-us-east-1}

# --- Argument Parsing ---
# Initialize variables
PROJECT_NAME=""
S3_BUCKET=""
STACK_NAME=""
KEY_PAIR_NAME=""
NEW_RELIC_LICENSE_KEY=""
NEW_RELIC_ACCOUNT_ID=""

# Parse named arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --project-name) PROJECT_NAME="$2"; shift ;;
        --bucket) S3_BUCKET="$2"; shift ;;
        --stack) STACK_NAME="$2"; shift ;;
        --key-pair) KEY_PAIR_NAME="$2"; shift ;;
        --nr-license-key) NEW_RELIC_LICENSE_KEY="$2"; shift ;;
        --nr-account-id) NEW_RELIC_ACCOUNT_ID="$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [ -z "$PROJECT_NAME" ] || [ -z "$S3_BUCKET" ] || [ -z "$STACK_NAME" ] || [ -z "$KEY_PAIR_NAME" ] || [ -z "$NEW_RELIC_LICENSE_KEY" ] || [ -z "$NEW_RELIC_ACCOUNT_ID" ]; then
    echo "Usage: $0 --project-name <PROJECT_NAME> --bucket <S3_BUCKET_NAME> --stack <STACK_NAME> --key-pair <EC2_KEY_PAIR_NAME> --nr-license-key <NEW_RELIC_LICENSE_KEY> --nr-account-id <NEW_RELIC_ACCOUNT_ID>"
    exit 1
fi

# Automatically detect public IP address
# Note: This requires the 'dig' command-line tool (part of dnsutils/bind-utils)
MY_IP=$(dig +short myip.opendns.com @resolver1.opendns.com)/32
if [ -z "$MY_IP" ]; then
    echo "Could not determine public IP address."
    exit 1
fi
echo "--- Automatically detected public IP for SSH: $MY_IP ---"


echo "--- Preparing Lambda Deployment Packages ---"
# Create a temporary directory for packaging
mkdir -p build
# Remove old packages if they exist
rm -f build/$FUNCTION_PACKAGE_NAME

# Zip the contents of the lambda directory for the function code
(cd lambda && zip -r ../build/$FUNCTION_PACKAGE_NAME app.py)

# Check if the New Relic layer zip exists
if [ ! -f "lambda/$LAYER_PACKAGE_NAME" ]; then
    echo "Error: New Relic layer package 'lambda/$LAYER_PACKAGE_NAME' not found."
    echo "Please download it and place it in the 'lambda' directory."
    exit 1
fi


echo "--- Uploading Packages to S3 ---"
aws s3 cp build/$FUNCTION_PACKAGE_NAME s3://$S3_BUCKET/$FUNCTION_PACKAGE_NAME
aws s3 cp lambda/$LAYER_PACKAGE_NAME s3://$S3_BUCKET/$LAYER_PACKAGE_NAME


echo "--- Deploying CloudFormation Stack ---"
# The 'deploy' command handles both creation and updates
aws cloudformation deploy \
    --template-file cloudformation.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --region $REGION \
    --parameter-overrides \
        ProjectName=$PROJECT_NAME \
        LambdaS3Bucket=$S3_BUCKET \
        LambdaS3Key=$FUNCTION_PACKAGE_NAME \
        LambdaLayerS3Key=$LAYER_PACKAGE_NAME \
        KeyName=$KEY_PAIR_NAME \
        MyIpAddress=$MY_IP \
        NewRelicLicenseKey=$NEW_RELIC_LICENSE_KEY \
        NewRelicAccountId=$NEW_RELIC_ACCOUNT_ID

echo ""
echo "✅ Deployment initiated for stack '$STACK_NAME'."
echo "Waiting for stack deployment to complete..."

# The 'deploy' command is synchronous and waits for completion, so no extra 'wait' is needed.

echo "--- Deployment Complete! Fetching Outputs... ---"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs" \
    --output table \
    --region "$REGION"

echo ""
echo "Next steps are in the README.md"
