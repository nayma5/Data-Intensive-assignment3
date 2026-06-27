from uuid import uuid4

from src.tests.utils import upload_review, wait_until_processed, wait_until_preprocessed, get_user


def unique_key(name):
    return f"tests/{name}_{uuid4().hex}.json"


def test_preprocessing_review():
    review = {
        "reviewerID": "prep_user",
        "summary": "The dogs are amazing",
        "reviewText": "I bought 2 items and they were working well",
        "overall": 5
    }

    key = unique_key("preprocessing")
    upload_review(review, key)
    result = wait_until_preprocessed(key)

    assert "the" not in result["cleaned_words"]
    assert "and" not in result["cleaned_words"]
    assert "dogs" in result["cleaned_words"]
    assert "dog" in result["lemmas"]
    assert "buy" in result["lemmas"]
    assert "work" in result["lemmas"]
    assert result["overall"] == 5

def test_positive_review():
    review = {
        "reviewerID": "alice",
        "summary": "Excellent",
        "reviewText": "Amazing product",
        "overall": 5
    }

    key = unique_key("positive")
    upload_review(review, key)
    result = wait_until_processed(key)

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

    key = unique_key("negative")
    upload_review(review, key)
    result = wait_until_processed(key)

    assert result["sentiment"] == "negative"


def test_profanity():
    review = {
        "reviewerID": "charlie",
        "summary": "Bad",
        "reviewText": "This is shit",
        "overall": 1
    }

    key = unique_key("profane")
    upload_review(review, key)
    result = wait_until_processed(key)

    assert result["passed_profanity_check"] is False
    assert result["is_impolite"] is True
    assert "shit" in result["profanity_words"]


def test_ban_user():
    user_id = f"banned_user_{uuid4().hex}"

    review = {
        "reviewerID": user_id,
        "summary": "Bad",
        "reviewText": "shit",
        "overall": 1
    }

    for i in range(4):
        key = unique_key(f"ban_{user_id}_{i}")
        upload_review(review, key)
        wait_until_processed(key)

    user = get_user(user_id)

    assert int(user["impoliteReviewCount"]) == 4
    assert user["isBanned"] is True
