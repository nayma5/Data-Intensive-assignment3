import json
import time
import boto3

ENDPOINT = "http://localhost:4566"

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1"
)

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1"
)

RAW_BUCKET = "review-app-raw"
ANALYZED_BUCKET = "review-app-analyzed"
USERS_TABLE = "review-app-users"


def upload_review(review, key):
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(review)
    )


def wait_until_processed(key, timeout=20):
    analyzed_key = key.replace(".json", "_analyzed.json")

    start = time.time()
    while time.time() - start < timeout:
        try:
            obj = s3.get_object(
                Bucket=ANALYZED_BUCKET,
                Key=analyzed_key
            )
            return json.loads(obj["Body"].read().decode())
        except Exception:
            time.sleep(1)

    raise TimeoutError("Review not processed in time")
def get_user(reviewer_id):
    table = dynamodb.Table(USERS_TABLE)
    response = table.get_item(Key={"reviewerID": reviewer_id})
    return response.get("Item")
