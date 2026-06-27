import json
import time
import os
import subprocess
import boto3
from uuid import uuid4

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

LOCAL_DATASET = "reviews_devset.json"
HDFS_DATASET = "/dic_shared/amazon-reviews/full/reviews_devset.json"

positive = 0
neutral = 0
negative = 0
profane = 0
count = 0
run_id = uuid4().hex
dataset_reviewer_ids = set()


def process_review(review, i, timeout=60):
    global positive, neutral, negative, profane, count

    key = f"dataset_runs/{run_id}/dataset_review_{i}.json"
    reviewer_id = review.get("reviewerID")
    if reviewer_id:
        dataset_reviewer_ids.add(reviewer_id)

    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=json.dumps(review)
    )

    analyzed_key = key.replace(".json", "_analyzed.json")

    start = time.time()
    while time.time() - start < timeout:
        try:
            obj = s3.get_object(
                Bucket=ANALYZED_BUCKET,
                Key=analyzed_key
            )
            result = json.loads(obj["Body"].read().decode())
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise TimeoutError(f"Review {key} was not processed in time")

    sentiment = result["sentiment"]

    if sentiment == "positive":
        positive += 1
    elif sentiment == "neutral":
        neutral += 1
    else:
        negative += 1

    if result["is_impolite"]:
        profane += 1

    count += 1

    if count % 500 == 0:
        print(f"Processed {count}")


print("Starting dataset processing...")

if os.path.exists(LOCAL_DATASET):
    print("Using local dataset copy...")
    with open(LOCAL_DATASET, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            review = json.loads(line.strip())
            process_review(review, i)

else:
    print("Local dataset not found. Reading from HDFS...")
    proc = subprocess.Popen(
        ["hdfs", "dfs", "-cat", HDFS_DATASET],
        stdout=subprocess.PIPE,
        text=True
    )

    for i, line in enumerate(proc.stdout):
        review = json.loads(line.strip())
        process_review(review, i)

table = dynamodb.Table(USERS_TABLE)
items = []
scan_kwargs = {}

while True:
    response = table.scan(**scan_kwargs)
    items.extend(response["Items"])
    if "LastEvaluatedKey" not in response:
        break
    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

banned_users = []
for item in items:
    if item.get("reviewerID") in dataset_reviewer_ids and item.get("isBanned"):
        banned_users.append(item["reviewerID"])

print("\n===== RESULTS =====")
print("Total:", count)
print("Positive:", positive)
print("Neutral:", neutral)
print("Negative:", negative)
print("Profane:", profane)
print("Banned users:", len(banned_users))
print(banned_users)
