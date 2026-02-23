from app.model import predict_text


def test_predict_spam() -> None:
    pred = predict_text("Limited time offer, click now to win")
    assert pred.label == "spam"


def test_predict_ham() -> None:
    pred = predict_text("Let's meet tomorrow for coffee")
    assert pred.label == "ham"
