# Data Intensive Assignment 3

This repository contains Assignment 3 of the Data Intensive Systems course.

## Implemented Task

Implemented the review preprocessing pipeline:

- Created the `preprocessing` Lambda function
- Read review JSON files from the input S3 bucket
- Cleaned and tokenized review text
- Removed predefined stop words
- Stored the processed review in the output S3 bucket
- Configured automatic S3 event triggering for the preprocessing Lambda

## Main Files

- `lambdas/preprocessing/handler.py` – preprocessing logic
- `lambdas/preprocessing/requirements.txt` – Lambda dependencies
- `run.sh` – deployment and infrastructure setup
- `architecture.png` – system architecture

## Example Output

Input review:

```json
{
  "summary": "Good product",
  "reviewText": "I really liked this product. It works very well!"
}