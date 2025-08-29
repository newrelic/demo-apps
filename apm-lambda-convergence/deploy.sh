#!/bin/bash
set -e

# Check for required arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <S3_BUCKET_NAME> <STACK_NAME>"
    exit 1
fi

S3_BUCKET=$1
STACK_NAME=$2
PACKAGE_NAME="lambda_package.zip"
REGION=${AWS_REGION:-us-east-1}

echo "--- Preparing Lambda Deployment Package ---"
# Create a temporary directory for packaging
mkdir -p build
# Remove old package if it exists
rm -f build/$PACKAGE_NAME
# Zip the contents of the lambda directory
(cd lambda && zip -r ../build/$PACKAGE_NAME .)

echo "--- Uploading Package to S3 ---"
aws s3 cp build/$PACKAGE_NAME s3://$S3_BUCKET/$PACKAGE_NAME

echo "--- Deploying CloudFormation Stack ---"
aws cloudformation deploy \
    --template-file template.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --parameter-overrides \
        LambdaS3Bucket=$S3_BUCKET \
        LambdaS3Key=$PACKAGE_NAME

echo ""
echo "✅ Deployment initiated for stack '$STACK_NAME'."
echo "Check the AWS CloudFormation console in the '$REGION' region for status."