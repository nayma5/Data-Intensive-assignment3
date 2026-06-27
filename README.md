# Data Intensive Assignment 3

The implemented event-driven pipeline is:

```text
Raw review S3
→ preprocessing Lambda
→ profanity-check Lambda
→ sentiment-analysis Lambda
→ user-tracking Lambda
→ DynamoDB customer count and ban status
```

Bucket and table names are stored in SSM Parameter Store.

## Requirements

Install the requirements with:

```bash
pip install -r requirements.txt
```


## Run

Start MiniStack in one terminal:

```bash
ministack
```

In another terminal:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

bash run.sh
```

## Upload a review

For this we provide a sample review under `src/sample_review.json`.

```bash
aws --endpoint-url=http://localhost:4566 \
  s3 cp src/sample_review.json s3://review-app-raw/sample_review.json
```

Inspect the final analyzed review:

```bash
aws --endpoint-url=http://localhost:4566 s3 cp \
  s3://review-app-analyzed/sample_review_analyzed.json -
```

Inspect customer counts and ban status:

```bash
aws --endpoint-url=http://localhost:4566 dynamodb scan \
  --table-name review-app-users
```

An impolite review increments `impoliteReviewCount`. A customer is marked with
`isBanned: true` after more than three impolite reviews.

## Implemented functionality

- Tokenization and stop-word removal
- Simple lemmatization
- Profanity checking
- Sentiment analysis
- Counting impolite reviews per customer
- Banning customers after their fourth impolite review

## Automated Integration Tests

We have in total 5 tests - preprocessing, positive review, negative review, profanity and banning of an user. Run all tests using:

```bash
python3 -m pytest src/tests -v
```

## Full dataset

Run the full dataset processor using:

```bash
python3 src/scripts/run_dataset.py
```

## Dataset Results

Dataset used:
`/dic_shared/amazon-reviews/full/reviews_devset.json`

Final results after processing:

- Total Reviews Processed: 78,829
- Positive Reviews: 68,549
- Neutral Reviews: 3,956
- Negative Reviews: 6,324
- Profane Reviews: 873
- Banned Users: 0
