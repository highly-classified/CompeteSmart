"""
utils.py
--------
Shared utilities for text processing.

Responsibilities
----------------
* clean_text()      – strip noise from raw extracted strings
* chunk_text()      – split cleaned text into 5–30 word semantic chunks
* compute_hash()    – SHA-256 fingerprint for deduplication
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")
_NOISE_RE = re.compile(
    r"(cookie|©|\bprivacy policy\b|\bterms of service\b|\ball rights reserved\b)",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """
    Normalise and clean a raw string:
    1. Unicode NFKC normalisation
    2. Remove non-printable / control characters
    3. Collapse whitespace
    4. Strip leading/trailing whitespace
    """
    # NFKC normalisation (e.g. ﬁ → fi, &nbsp; → space)
    text = unicodedata.normalize("NFKC", text)

    # Drop control characters except normal whitespace
    text = "".join(
        ch for ch in text if unicodedata.category(ch)[0] != "C" or ch in " \t\n"
    )

    # Collapse whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text


def is_noise(text: str) -> bool:
    """Return True if the text is clearly noise and should be discarded."""
    return bool(_NOISE_RE.search(text))


# ---------------------------------------------------------------------------
# Semantic chunking
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """
    Lightweight sentence splitter using punctuation boundaries.
    Falls back to the whole string when no boundary is found.
    """
    # Split on . ! ? followed by whitespace or end-of-string
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    min_words: int = 5,
    max_words: int = 30,
) -> list[str]:
    """
    Split *text* into semantic chunks where each chunk:
    * contains between *min_words* and *max_words* words (inclusive)
    * represents a single coherent idea

    Strategy
    --------
    1. Split text into sentences.
    2. Walk sentences word-by-word; accumulate words into a buffer.
    3. When buffer hits *max_words*, emit the chunk.
    4. A sentence boundary that yields a buffer of >= *min_words* also emits.
    5. Discard buffers shorter than *min_words*.
    """
    sentences = _split_sentences(text)
    chunks: list[str] = []
    buffer: list[str] = []

    for sentence in sentences:
        words = sentence.split()

        for word in words:
            buffer.append(word)
            if len(buffer) >= max_words:
                chunk = " ".join(buffer)
                if len(buffer) >= min_words:
                    chunks.append(chunk)
                buffer = []

        # End of sentence: flush buffer if it meets minimum
        if len(buffer) >= min_words:
            chunks.append(" ".join(buffer))
            buffer = []
        # Otherwise carry the short buffer into the next sentence so we can
        # potentially merge it to meet the minimum threshold.

    # Final flush – discard if too short
    if len(buffer) >= min_words:
        chunks.append(" ".join(buffer))

    return chunks


# ---------------------------------------------------------------------------
# Hashing / deduplication
# ---------------------------------------------------------------------------

def compute_hash(text: str) -> str:
    """Return a hex SHA-256 digest of *text* (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
