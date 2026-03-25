"""
utils.py
--------
Shared utilities: URL normalisation, text processing, chunking, hashing.

Responsibilities
----------------
* normalize_url()   – canonical form of a URL (no trailing slash, lowercase scheme+host)
* clean_text()      – strip noise from raw extracted strings
* chunk_text()      – split cleaned text into 5–30 word semantic chunks
* compute_hash()    – SHA-256 fingerprint for deduplication
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from urllib.parse import urlparse, urlunparse


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------

def normalize_url(url: str) -> str:
    """
    Return the canonical form of *url* so that the same page is never stored
    under two different strings.

    Rules applied (in order)
    ------------------------
    1. Strip leading/trailing whitespace.
    2. Lowercase the scheme and host (path is case-sensitive for many servers).
    3. Remove a trailing slash from the path ONLY when the path is exactly "/"
       or ends with "/" and has no query string — avoids mangling paths like
       "/chennai/home-cleaning/".
    4. Remove the fragment (#…) — fragments are client-side only.

    Examples
    --------
    >>> normalize_url("https://www.urbancompany.com/")
    'https://www.urbancompany.com'
    >>> normalize_url("HTTPS://WWW.urbancompany.com/chennai")
    'https://www.urbancompany.com/chennai'
    >>> normalize_url("https://www.urbancompany.com/services/")
    'https://www.urbancompany.com/services'
    """
    url = url.strip()
    parsed = urlparse(url)

    # Lowercase scheme + host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip trailing slash from path (unless path is empty)
    path = parsed.path
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")

    # Drop fragment; keep query string as-is
    normalised = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
    return normalised


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
