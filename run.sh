#!/usr/bin/env bash

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://localhost:4566,http://127.0.0.1:4566,https://lbd.tuwien.ac.at}"
export MINISTACK_ENDPOINT=http://localhost:4566

AWS="aws --endpoint-url=${MINISTACK_ENDPOINT}"

ON_LBD_PROXY=0
if [ -n "${JUPYTERHUB_USER:-}" ] || [ -n "${JUPYTERHUB_SERVICE_PREFIX:-}" ]; then
  ON_LBD_PROXY=1
fi

if [ -z "${S3_ENDPOINT_URL:-}" ]; then
  if [ "${ON_LBD_PROXY}" -eq 1 ] && [ -n "${USER:-}" ] && [ "${USER}" != "root" ]; then
    export S3_ENDPOINT_URL="https://lbd.tuwien.ac.at/user/${USER}/proxy/4566"
  else
    export S3_ENDPOINT_URL=""
  fi
fi

if [ -z "${PUBLIC_BASE_URL:-}" ]; then
  if [ "${ON_LBD_PROXY}" -eq 1 ] && [ -n "${USER:-}" ] && [ "${USER}" != "root" ]; then
    export PUBLIC_BASE_URL="https://lbd.tuwien.ac.at/user/${USER}/proxy/4566"
  else
    export PUBLIC_BASE_URL="http://localhost:4566"
  fi
fi

PRESIGN_LIST_ENV="{\"STAGE\":\"local\",\"ALLOWED_ORIGINS\":\"${ALLOWED_ORIGINS}\""
if [ -n "${S3_ENDPOINT_URL}" ]; then
  PRESIGN_LIST_ENV="${PRESIGN_LIST_ENV},\"S3_ENDPOINT_URL\":\"${S3_ENDPOINT_URL}\""
fi
PRESIGN_LIST_ENV="${PRESIGN_LIST_ENV}}"

### Create buckets
${AWS} s3 mb s3://ministack-thumbnails-app-images || true
${AWS} s3 mb s3://ministack-thumbnails-app-resized || true
${AWS} s3 mb s3://review-app-preprocessed || true
${AWS} s3 mb s3://webapp || true

### Store bucket names in SSM
${AWS} ssm put-parameter \
 --name /ministack-thumbnail-app/buckets/images \
 --type "String" \
 --value "ministack-thumbnails-app-images" \
 --overwrite

${AWS} ssm put-parameter \
 --name /ministack-thumbnail-app/buckets/resized \
 --type "String" \
 --value "ministack-thumbnails-app-resized" \
 --overwrite

${AWS} ssm put-parameter \
 --name /review-app/buckets/preprocessed \
 --type "String" \
 --value "review-app-preprocessed" \
 --overwrite

### Presign Lambda
${AWS} lambda delete-function --function-name presign 2>/dev/null || true
(cd lambdas/presign; rm -f lambda.zip; zip lambda.zip handler.py)

${AWS} lambda create-function \
 --function-name presign \
 --runtime python3.11 \
 --timeout 10 \
 --zip-file fileb://lambdas/presign/lambda.zip \
 --handler handler.handler \
 --role arn:aws:iam::000000000000:role/lambda-role \
 --environment "{\"Variables\":${PRESIGN_LIST_ENV}}"

${AWS} lambda create-function-url-config \
 --function-name presign \
 --auth-type NONE 2>/dev/null || true

### List Lambda
${AWS} lambda delete-function --function-name list 2>/dev/null || true
(cd lambdas/list; rm -f lambda.zip; zip lambda.zip handler.py)

${AWS} lambda create-function \
 --function-name list \
 --runtime python3.11 \
 --timeout 10 \
 --zip-file fileb://lambdas/list/lambda.zip \
 --handler handler.handler \
 --role arn:aws:iam::000000000000:role/lambda-role \
 --environment "{\"Variables\":${PRESIGN_LIST_ENV}}"

${AWS} lambda create-function-url-config \
 --function-name list \
 --auth-type NONE 2>/dev/null || true

### Preprocessing Lambda
${AWS} lambda delete-function --function-name preprocessing 2>/dev/null || true

(
 cd lambdas/preprocessing
 rm -rf package lambda.zip
 mkdir package
 pip install -r requirements.txt -t package --platform manylinux2014_x86_64 --only-binary=:all:
 zip lambda.zip handler.py
 cd package
 zip -r ../lambda.zip *
)

${AWS} lambda delete-function --function-name preprocessing 2>/dev/null || true
${AWS} lambda create-function \
 --function-name preprocessing \
 --runtime python3.11 \
 --timeout 10 \
 --zip-file fileb://lambdas/preprocessing/lambda.zip \
 --handler handler.handler \
 --role arn:aws:iam::000000000000:role/lambda-role \
 --environment "{\"Variables\":{\"STAGE\":\"local\"}}"

sleep 3

PREPROCESSING_ARN=$(${AWS} lambda get-function \
 --function-name preprocessing \
 --query 'Configuration.FunctionArn' \
 --output text)

echo "Preprocessing ARN: ${PREPROCESSING_ARN}"

if [ -z "${PREPROCESSING_ARN}" ]; then
  echo "ERROR: Preprocessing ARN is empty."
  exit 1
fi

### Connect S3 upload event to preprocessing Lambda
${AWS} s3api put-bucket-notification-configuration \
 --bucket ministack-thumbnails-app-images \
 --notification-configuration "{\"LambdaFunctionConfigurations\":[{\"LambdaFunctionArn\":\"${PREPROCESSING_ARN}\",\"Events\":[\"s3:ObjectCreated:*\"]}]}"

### Static webapp
${AWS} s3 website s3://webapp --index-document index.html
${AWS} s3 sync --delete ./website s3://webapp --exclude ".ipynb_checkpoints/*"

echo
echo "Visit the following URL to access the web app:"
echo "Public web app URL: ${PUBLIC_BASE_URL}/webapp/index.html"
echo "Public presign URL: ${PUBLIC_BASE_URL}/2015-03-31/functions/presign/invocations"
echo "Public list URL: ${PUBLIC_BASE_URL}/2015-03-31/functions/list/invocations"

if [ -n "${S3_ENDPOINT_URL}" ]; then
  echo "Public S3 endpoint URL: ${S3_ENDPOINT_URL}"
fi