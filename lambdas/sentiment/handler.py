import json
import os
from urllib.parse import unquote_plus

import boto3


endpoint_url = None
if os.getenv("STAGE") == "local":
    endpoint_url = "http://localhost:4566"

s3 = boto3.client("s3", endpoint_url=endpoint_url)
ssm = boto3.client("ssm", endpoint_url=endpoint_url)


POSITIVE_WORDS = {
    "amazing", "awesome", "best", "comfortable", "easy", "excellent",
    "fantastic", "fast", "good", "great", "happy", "helpful", "like",
    "love", "nice", "perfect", "recommend", "reliable", "satisfied",
    "useful", "well", "wonderful", "work",
}

NEGATIVE_WORDS = {
    "awful", "bad", "broken", "cheap", "difficult", "disappointed",
    "disappointing", "failure", "hate", "horrible", "poor", "problem",
    "refund", "slow", "terrible", "uncomfortable", "unhappy", "useless",
    "waste", "worst",
}

NEGATIONS = {"not", "never", "no"}


def get_output_bucket_name():
    parameter = ssm.get_parameter(Name="/review-app/buckets/analyzed")
    return parameter["Parameter"]["Value"]


def word_sentiment_score(tokens):
    score = 0
    negate_next = False

    for word in tokens:
        if word in NEGATIONS:
            negate_next = True
            continue

        value = int(word in POSITIVE_WORDS) - int(word in NEGATIVE_WORDS)
        if negate_next and value:
            value *= -1
        score += value
        negate_next = False

    return score


def rating_sentiment_score(overall):
    try:
        rating = float(overall)
    except (TypeError, ValueError):
        return 0

    if rating >= 4:
        return 1
    if rating <= 2:
        return -1
    return 0


def analyze_sentiment(review):
    text_score = word_sentiment_score(review.get("lemmas", []))
    rating_score = rating_sentiment_score(review.get("overall"))
    score = text_score + rating_score

    if score > 0:
        label = "positive"
    elif score < 0:
        label = "negative"
    else:
        label = "neutral"

    return {
        **review,
        "sentiment": label,
        "sentiment_score": score,
    }


def make_output_key(key):
    suffix = "_profanity_checked.json"
    base = key[:-len(suffix)] if key.lower().endswith(suffix) else key.removesuffix(".json")
    return f"{base}_analyzed.json"


def handler(event, context):
    output_bucket = get_output_bucket_name()

    for record in event.get("Records", []):
        input_bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        response = s3.get_object(Bucket=input_bucket, Key=key)
        review = json.loads(response["Body"].read().decode("utf-8"))
        analyzed_review = analyze_sentiment(review)

        s3.put_object(
            Bucket=output_bucket,
            Key=make_output_key(key),
            Body=json.dumps(analyzed_review),
            ContentType="application/json",
        )

    return {"statusCode": 200}
