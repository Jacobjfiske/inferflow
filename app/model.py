from dataclasses import dataclass


@dataclass
class Prediction:
    label: str
    score: float


SPAM_KEYWORDS = {
    "free",
    "win",
    "offer",
    "click",
    "urgent",
    "limited time",
    "prize",
}


def predict_text(text: str) -> Prediction:
    lowered = text.lower()
    hits = sum(1 for kw in SPAM_KEYWORDS if kw in lowered)

    if hits >= 2:
        return Prediction(label="spam", score=min(0.99, 0.55 + hits * 0.1))

    return Prediction(label="ham", score=max(0.51, 0.9 - hits * 0.05))
