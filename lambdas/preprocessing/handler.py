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

IRREGULAR_LEMMAS = {
    "bought": "buy",
    "better": "good",
    "liked": "like",
    "loved": "love",
    "loving": "love",
    "went": "go",
    "working": "work",
    "worse": "bad",
    "worst": "bad",
}


def get_output_bucket_name():
    """Fetch the preprocessing output bucket name from SSM.

    Returns:
        The S3 bucket name used for preprocessed reviews.
    """
    parameter = ssm.get_parameter(Name="/review-app/buckets/preprocessed")
    return parameter["Parameter"]["Value"]


def lemmatize_word(word):
    """Reduce a token to a simple lemma.

    Args:
        word: Token to normalize.

    Returns:
        A normalized version of the input token.
    """
    if word in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[word]
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def clean_text(text):
    """Tokenize text and remove punctuation and stop words.

    Args:
        text: Raw review text to clean.

    Returns:
        A list of cleaned lowercase tokens.
    """
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)

    words = text.split()
    cleaned_words = []

    for word in words:
        if word not in STOP_WORDS:
            cleaned_words.append(word)

    return cleaned_words


def preprocess_review(review):
    """Create the preprocessed representation of a review.

    Args:
        review: Raw review dictionary from the input S3 object.

    Returns:
        Review data with cleaned tokens and simple lemmas added.
    """
    summary = review.get("summary", "")
    review_text = review.get("reviewText", "")
    cleaned_words = clean_text(summary + " " + review_text)

    return {
        "reviewerID": review.get("reviewerID"),
        "asin": review.get("asin"),
        "overall": review.get("overall"),
        "summary": summary,
        "reviewText": review_text,
        "cleaned_words": cleaned_words,
        "lemmas": [lemmatize_word(word) for word in cleaned_words],
    }


def handler(event, context):
    """Handle S3 object-created events for raw review files.

    Args:
        event: Lambda event containing S3 records.
        context: Lambda runtime context.

    Returns:
        Status dictionary for the Lambda invocation.
    """
    if event.get("Event") == "s3:TestEvent":
        return {"statusCode": 200}

    output_bucket = get_output_bucket_name()

    for record in event.get("Records", []):
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
