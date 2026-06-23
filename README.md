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

```bash
aws --endpoint-url=http://localhost:4566 \
  s3 cp sample_review.json s3://review-app-raw/
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

Automated integration tests, dataset results, the final architecture diagram,
and submission documents are still to be completed.
