import json
import os
from urllib.parse import unquote_plus

import boto3


endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)
dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)


def get_users_table():
    """Fetch the DynamoDB users table configured in SSM.

    Returns:
        DynamoDB table resource for customer tracking.
    """
    parameter = ssm.get_parameter(Name="/review-app/tables/users")
    return dynamodb.Table(parameter["Parameter"]["Value"])


def update_customer(review):
    """Update a customer's impolite review count and ban status.

    Args:
        review: Analyzed review dictionary.
    """
    reviewer_id = review.get("reviewerID")
    if not reviewer_id:
        return

    table = get_users_table()

    if not review.get("is_impolite", False):
        table.update_item(
            Key={"reviewerID": reviewer_id},
            UpdateExpression=(
                "SET impoliteReviewCount = if_not_exists(impoliteReviewCount, :zero), "
                "isBanned = if_not_exists(isBanned, :false)"
            ),
            ExpressionAttributeValues={":zero": 0, ":false": False},
        )
        return

    response = table.update_item(
        Key={"reviewerID": reviewer_id},
        UpdateExpression=(
            "SET isBanned = if_not_exists(isBanned, :false) "
            "ADD impoliteReviewCount :one"
        ),
        ExpressionAttributeValues={":one": 1, ":false": False},
        ReturnValues="ALL_NEW",
    )

    if response["Attributes"]["impoliteReviewCount"] > 3:
        table.update_item(
            Key={"reviewerID": reviewer_id},
            UpdateExpression="SET isBanned = :true",
            ExpressionAttributeValues={":true": True},
        )


def handler(event, context):
    """Handle S3 events for analyzed review files.

    Args:
        event: Lambda event containing S3 records.
        context: Lambda runtime context.

    Returns:
        Status dictionary for the Lambda invocation.
    """
    if event.get("Event") == "s3:TestEvent":
        return {"statusCode": 200}

    for record in event.get("Records", []):
        input_bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        response = s3.get_object(Bucket=input_bucket, Key=key)
        review = json.loads(response["Body"].read().decode("utf-8"))
        update_customer(review)

    return {"statusCode": 200}
