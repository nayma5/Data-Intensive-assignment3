import json
import os
import re
from urllib.parse import unquote_plus

import boto3


endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)


STOP_WORDS = {
    "a", "an", "the", "and", "or", "but",
    "is", "are", "was", "were",
    "i", "me", "my", "we", "our",
    "this", "that", "it", "to", "of", "for", "in", "on",
}


def get_output_bucket_name():
    parameter = ssm.get_parameter(Name="/review-app/buckets/preprocessed")
    return parameter["Parameter"]["Value"]


def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)

    words = text.split()
    cleaned_words = []

    for word in words:
        if word not in STOP_WORDS:
            cleaned_words.append(word)

    return cleaned_words


def preprocess_review(review):
    summary = review.get("summary", "")
    review_text = review.get("reviewText", "")

    full_text = summary + " " + review_text

    return {
        "reviewerID": review.get("reviewerID"),
        "asin": review.get("asin"),
        "overall": review.get("overall"),
        "summary": summary,
        "reviewText": review_text,
        "cleaned_words": clean_text(full_text),
    }

def handler(event, context):
    output_bucket = get_output_bucket_name()

    for record in event["Records"]:
        input_bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        response = s3.get_object(Bucket=input_bucket, Key=key)
        review = json.loads(response["Body"].read().decode("utf-8"))

        processed_review = preprocess_review(review)

        output_key = key.replace(".json", "_preprocessed.json")

        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=json.dumps(processed_review),
            ContentType="application/json",
        )

    return {"statusCode": 200}