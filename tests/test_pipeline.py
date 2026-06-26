import time
from tests.utils import upload_review, wait_until_processed, get_user

def test_positive_review():
    review = {
        "reviewerID": "alice",
        "summary": "Excellent",
        "reviewText": "Amazing product",
        "overall": 5
    }

    upload_review(review, "positive.json")
    result = wait_until_processed("positive.json")

    assert result["sentiment"] == "positive"
    assert result["passed_profanity_check"] is True
    assert result["is_impolite"] is False


def test_negative_review():
    review = {
        "reviewerID": "bob",
        "summary": "Terrible",
        "reviewText": "Worst purchase ever",
        "overall": 1
    }

    upload_review(review, "negative.json")
    result = wait_until_processed("negative.json")

    assert result["sentiment"] == "negative"


def test_profanity():
    review = {
        "reviewerID": "charlie",
        "summary": "Bad",
        "reviewText": "This is shit",
        "overall": 1
    }

    upload_review(review, "profane.json")
    result = wait_until_processed("profane.json")

    assert result["passed_profanity_check"] is False
    assert result["is_impolite"] is True
    assert "shit" in result["profanity_words"]


def test_ban_user():
    user_id = f"banned_user_{int(time.time())}"

    review = {
        "reviewerID": user_id,
        "summary": "Bad",
        "reviewText": "shit",
        "overall": 1
    }

    for i in range(4):
        key = f"ban_{user_id}_{i}.json"
        upload_review(review, key)
        wait_until_processed(key)

    user = get_user(user_id)

    assert int(user["impoliteReviewCount"]) == 4
    assert user["isBanned"] is True
