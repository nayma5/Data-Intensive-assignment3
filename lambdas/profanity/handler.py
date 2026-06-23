import json
import os
from urllib.parse import unquote_plus

import boto3


endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)


PROFANE_WORDS = {
    "asshole",
    "bastard",
    "bitch",
    "bullshit",
    "crap",
    "damn",
    "dick",
    "fuck",
    "fucking",
    "idiot",
    "moron",
    "shit",
    "stupid",
}


def get_output_bucket_name():
    parameter = ssm.get_parameter(Name="/review-app/buckets/profanity-checked")
    return parameter["Parameter"]["Value"]


def check_profanity(review):
    cleaned_words = review.get("cleaned_words", [])
    found_words = sorted({word for word in cleaned_words if word in PROFANE_WORDS})

    return {
        **review,
        "profanity_words": found_words,
        "passed_profanity_check": not found_words,
        "is_impolite": bool(found_words),
    }


def make_output_key(key):
    suffix = "_preprocessed.json"
    base = key[:-len(suffix)] if key.lower().endswith(suffix) else key.removesuffix(".json")
    return f"{base}_profanity_checked.json"


def handler(event, context):
    output_bucket = get_output_bucket_name()

    for record in event.get("Records", []):
        input_bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        response = s3.get_object(Bucket=input_bucket, Key=key)
        review = json.loads(response["Body"].read().decode("utf-8"))
        checked_review = check_profanity(review)

        s3.put_object(
            Bucket=output_bucket,
            Key=make_output_key(key),
            Body=json.dumps(checked_review),
            ContentType="application/json",
        )

    return {"statusCode": 200}
