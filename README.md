# Data Intensive Assignment 3

Implemented the **review preprocessing Lambda**.

The Lambda:

* Reads review JSON files from S3
* Combines the review summary and review text
* Converts text to lowercase
* Removes punctuation and special characters
* Removes predefined stop words
* Creates a list of cleaned words
* Stores the processed review in a separate S3 bucket
* Is triggered automatically when a new review is uploaded

## Project Structure

```text
lambdas/
├── list/
│   └── handler.py
├── preprocessing/
│   ├── handler.py
│   └── requirements.txt
└── presign/
    └── handler.py

website/
tests/

run.sh
architecture.png
README.md
```

## How to Run

1. Start Ministack.

2. Clone the repository:

```bash
git clone <repository-url>
cd Data-Intensive-assignment3
```

3. Deploy the infrastructure and Lambda functions:

```bash
bash run.sh
```

4. Upload a review JSON file:

```bash
aws --endpoint-url=http://localhost:4566 s3 cp review.json s3://ministack-thumbnails-app-images/
```

5. Verify that the preprocessing Lambda generated the output file:

```bash
aws --endpoint-url=http://localhost:4566 s3 ls s3://review-app-preprocessed
```

## Example

### Input

```json
{
  "summary": "Good product",
  "reviewText": "I really liked this product. It works very well!"
}
```

### Output

```json
{
  "cleaned_words": [
    "good",
    "product",
    "really",
    "liked",
    "product",
    "works",
    "very",
    "well"
  ]
}
```

## Note

The preprocessing component is already implemented and working.

If add new Lambda functions, buckets, or other infrastructure components, update `run.sh` and rerun:

```bash
bash run.sh
```

