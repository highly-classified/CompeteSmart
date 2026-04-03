import re
from collections import Counter
from typing import Iterable, List, Sequence, Tuple


CANONICAL_LABELS = {
    "Bathroom Cleaning",
    "Kitchen Cleaning",
    "Sofa Cleaning",
    "Pest Control",
    "Plumbing",
    "Appliance Repair",
    "Beauty",
    "Painting",
    "Electrical",
    "Cleaning",
    "General Service",
    "Others",
}

BASE_CATEGORY_KEYWORDS = {
    "Pest Control": {
        "pest": 3,
        "cockroach": 3,
        "termite": 3,
        "bug": 2,
        "insect": 2,
        "rodent": 2,
        "fumigation": 3,
    },
    "Plumbing": {
        "plumb": 3,
        "pipe": 2,
        "leak": 3,
        "drain": 3,
        "tap": 2,
        "faucet": 2,
        "sink": 2,
        "blockage": 3,
        "seepage": 3,
    },
    "Appliance Repair": {
        "ac": 2,
        "air conditioner": 3,
        "washing machine": 3,
        "fridge": 3,
        "refrigerator": 3,
        "appliance": 2,
        "microwave": 3,
        "geyser": 3,
        "repair": 2,
    },
    "Beauty": {
        "salon": 3,
        "facial": 3,
        "haircut": 3,
        "spa": 3,
        "wax": 2,
        "pedicure": 3,
        "manicure": 3,
        "beauty": 2,
    },
    "Painting": {
        "paint": 3,
        "wall": 2,
        "interior": 2,
        "exterior": 2,
        "waterproof": 2,
        "putty": 2,
        "texture": 2,
    },
    "Electrical": {
        "electric": 3,
        "wiring": 3,
        "switch": 2,
        "fan": 2,
        "socket": 2,
        "light": 2,
        "circuit": 3,
    },
    "Cleaning": {
        "clean": 3,
        "deep clean": 4,
        "home cleaning": 4,
        "sanitize": 3,
        "scrub": 2,
        "stain": 2,
        "dust": 2,
        "mop": 2,
    },
}

PRIORITY_SUBCATEGORIES = (
    ("Bathroom Cleaning", ("bathroom", "toilet", "washroom", "bath")),
    ("Kitchen Cleaning", ("kitchen",)),
    ("Sofa Cleaning", ("sofa", "couch", "upholstery")),
)

FILLER_WORDS = {
    "great",
    "best",
    "professional",
    "service",
    "services",
    "quality",
    "satisfied",
    "doorstep",
    "urban",
    "value",
    "money",
    "reviews",
    "review",
    "bookings",
    "booking",
    "trusted",
    "verified",
    "reliable",
    "affordable",
    "excellent",
    "premium",
    "budget",
    "friendly",
}


def clean_signal_text(text: str) -> str:
    if not text:
        return ""

    cleaned = text.lower()
    cleaned = re.sub(r"\b\d+(\.\d+)?\s*(k|m|l|cr)?\b", " ", cleaned)
    cleaned = re.sub(r"[₹$€£]\s*\d+(\.\d+)?", " ", cleaned)
    cleaned = re.sub(r"\b\d+\s*(mins?|minutes?|hours?|days?|rooms?|bathrooms?)\b", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _keyword_hits(text: str, keyword_weights: dict[str, int]) -> int:
    score = 0
    for keyword, weight in keyword_weights.items():
        pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
        if re.search(pattern, text):
            score += weight
    return score


def _priority_cleaning_label(text: str, cleaning_score: int) -> str | None:
    if cleaning_score <= 0:
        return None

    for label, keywords in PRIORITY_SUBCATEGORIES:
        for keyword in keywords:
            pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
            if re.search(pattern, text):
                return label
    return None


def _normalized_label(label: str) -> str:
    if not label:
        return "General Service"

    label = label.strip()
    if label in CANONICAL_LABELS:
        return label

    words = [w for w in re.findall(r"[A-Za-z]+", label) if w.lower() not in FILLER_WORDS]
    if not words:
        return "General Service"

    normalized = " ".join(words[:3]).title()
    return normalized if normalized in CANONICAL_LABELS else "General Service"


def generate_clean_label(texts: Sequence[str] | str) -> str:
    if isinstance(texts, str):
        source_texts = [texts]
    else:
        source_texts = [text for text in texts if text]

    combined_text = clean_signal_text(" ".join(source_texts[:5]))
    if not combined_text:
        return "General Service"

    scores = {
        category: _keyword_hits(combined_text, keywords)
        for category, keywords in BASE_CATEGORY_KEYWORDS.items()
    }

    priority_label = _priority_cleaning_label(combined_text, scores["Cleaning"])
    if priority_label:
        return priority_label

    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return "General Service"

    return _normalized_label(best_category)


def normalize_theme_label(label: str | None) -> str:
    if not label:
        return "General Service"

    label = label.strip()
    if label in CANONICAL_LABELS:
        return label

    return generate_clean_label(label)


def bucket_top_labels(counter: Counter, top_n: int = 5, include_others: bool = True) -> List[Tuple[str, int]]:
    items = [(label, value) for label, value in counter.most_common() if label != "General Service" and value > 0]
    top_items = items[:top_n]

    if not include_others:
        return top_items

    others_total = sum(value for _, value in items[top_n:])
    if others_total > 0:
        top_items.append(("Others", others_total))
    return top_items
