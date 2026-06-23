#!/usr/bin/env bash

set -e

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

MINISTACK_ENDPOINT="http://localhost:4566"
AWS="aws --endpoint-url=${MINISTACK_ENDPOINT}"

RAW_BUCKET="review-app-raw"
PREPROCESSED_BUCKET="review-app-preprocessed"
PROFANITY_BUCKET="review-app-profanity-checked"
ANALYZED_BUCKET="review-app-analyzed"
USERS_TABLE="review-app-users"

### Create the buckets used by the review pipeline
${AWS} s3 mb "s3://${RAW_BUCKET}" || true
${AWS} s3 mb "s3://${PREPROCESSED_BUCKET}" || true
${AWS} s3 mb "s3://${PROFANITY_BUCKET}" || true
${AWS} s3 mb "s3://${ANALYZED_BUCKET}" || true

### Create the DynamoDB table used for customer review counts
${AWS} dynamodb create-table \
  --table-name "${USERS_TABLE}" \
  --attribute-definitions AttributeName=reviewerID,AttributeType=S \
  --key-schema AttributeName=reviewerID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST >/dev/null 2>&1 || true

### Store bucket names in SSM Parameter Store
${AWS} ssm put-parameter \
  --name /review-app/buckets/raw \
  --type String \
  --value "${RAW_BUCKET}" \
  --overwrite

${AWS} ssm put-parameter \
  --name /review-app/buckets/preprocessed \
  --type String \
  --value "${PREPROCESSED_BUCKET}" \
  --overwrite

${AWS} ssm put-parameter \
  --name /review-app/buckets/profanity-checked \
  --type String \
  --value "${PROFANITY_BUCKET}" \
  --overwrite

${AWS} ssm put-parameter \
  --name /review-app/buckets/analyzed \
  --type String \
  --value "${ANALYZED_BUCKET}" \
  --overwrite

${AWS} ssm put-parameter \
  --name /review-app/tables/users \
  --type String \
  --value "${USERS_TABLE}" \
  --overwrite

### Package and deploy the Lambda functions
for function_name in preprocessing profanity sentiment user_tracking; do
  (
    cd "lambdas/${function_name}"
    rm -f lambda.zip
    zip lambda.zip handler.py
  )
done

${AWS} lambda delete-function --function-name preprocessing 2>/dev/null || true
${AWS} lambda create-function \
  --function-name preprocessing \
  --runtime python3.11 \
  --timeout 10 \
  --zip-file fileb://lambdas/preprocessing/lambda.zip \
  --handler handler.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --environment '{"Variables":{"STAGE":"local"}}'

${AWS} lambda delete-function --function-name profanity-check 2>/dev/null || true
${AWS} lambda create-function \
  --function-name profanity-check \
  --runtime python3.11 \
  --timeout 10 \
  --zip-file fileb://lambdas/profanity/lambda.zip \
  --handler handler.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --environment '{"Variables":{"STAGE":"local"}}'

${AWS} lambda delete-function --function-name sentiment-analysis 2>/dev/null || true
${AWS} lambda create-function \
  --function-name sentiment-analysis \
  --runtime python3.11 \
  --timeout 10 \
  --zip-file fileb://lambdas/sentiment/lambda.zip \
  --handler handler.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --environment '{"Variables":{"STAGE":"local"}}'

${AWS} lambda delete-function --function-name user-tracking 2>/dev/null || true
${AWS} lambda create-function \
  --function-name user-tracking \
  --runtime python3.11 \
  --timeout 10 \
  --zip-file fileb://lambdas/user_tracking/lambda.zip \
  --handler handler.handler \
  --role arn:aws:iam::000000000000:role/lambda-role \
  --environment '{"Variables":{"STAGE":"local"}}'

sleep 3

PREPROCESSING_ARN=$(${AWS} lambda get-function \
  --function-name preprocessing \
  --query Configuration.FunctionArn \
  --output text)

PROFANITY_ARN=$(${AWS} lambda get-function \
  --function-name profanity-check \
  --query Configuration.FunctionArn \
  --output text)

SENTIMENT_ARN=$(${AWS} lambda get-function \
  --function-name sentiment-analysis \
  --query Configuration.FunctionArn \
  --output text)

USER_TRACKING_ARN=$(${AWS} lambda get-function \
  --function-name user-tracking \
  --query Configuration.FunctionArn \
  --output text)

### Allow S3 to invoke each stage
${AWS} lambda add-permission \
  --function-name preprocessing \
  --statement-id raw-bucket-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${RAW_BUCKET}" >/dev/null

${AWS} lambda add-permission \
  --function-name profanity-check \
  --statement-id preprocessed-bucket-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${PREPROCESSED_BUCKET}" >/dev/null

${AWS} lambda add-permission \
  --function-name sentiment-analysis \
  --statement-id profanity-bucket-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${PROFANITY_BUCKET}" >/dev/null

${AWS} lambda add-permission \
  --function-name user-tracking \
  --statement-id analyzed-bucket-trigger \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn "arn:aws:s3:::${ANALYZED_BUCKET}" >/dev/null

### Connect the S3 event chain
${AWS} s3api put-bucket-notification-configuration \
  --bucket "${RAW_BUCKET}" \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${PREPROCESSING_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

${AWS} s3api put-bucket-notification-configuration \
  --bucket "${PREPROCESSED_BUCKET}" \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${PROFANITY_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

${AWS} s3api put-bucket-notification-configuration \
  --bucket "${PROFANITY_BUCKET}" \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${SENTIMENT_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

${AWS} s3api put-bucket-notification-configuration \
  --bucket "${ANALYZED_BUCKET}" \
  --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${USER_TRACKING_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

echo
echo "Review pipeline deployed."
echo "Upload one review JSON file to: s3://${RAW_BUCKET}"
echo "Final analyzed reviews appear in: s3://${ANALYZED_BUCKET}"
echo "Customer counts and ban status appear in DynamoDB table: ${USERS_TABLE}"
