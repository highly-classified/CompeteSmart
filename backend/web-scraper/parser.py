"""
parser.py
---------
HTML → high-quality semantic content extraction using BeautifulSoup4.

Design goals (v2)
-----------------
* Every output item is a self-contained semantic unit (5–25 words).
* Context expansion: short headings are merged with adjacent descriptive text
  so they carry meaning (e.g. "Sofa Cleaning" → "Professional sofa and carpet
  cleaning for your home, starting at ₹599").
* Multi-layer noise rejection: structural tags, CSS-class heuristics, regex
  blacklists, and word-count / uppercase guards all cooperate.
* Smart content_type labelling: service | cta | pricing | headline | paragraph.
* Normalized deduplication key: lowercased + whitespace-collapsed text, so
  near-identical phrases don't pollute the DB.
* Public interface unchanged: parse_page(html) → List[Tuple[str, str]]
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag

from utils import clean_text, is_noise

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# 1. STRUCTURAL NOISE — tags decomposed before any extraction
# ═══════════════════════════════════════════════════════════════════════════
_IGNORED_TAGS: set[str] = {
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "input", "select", "textarea",
    "svg", "img", "picture", "figure", "link", "meta",
}

# ═══════════════════════════════════════════════════════════════════════════
# 2. CSS CLASS / ID NOISE — elements whose class or id contain these strings
#    are skipped entirely (covers UC login, app-download, breadcrumbs, etc.)
# ═══════════════════════════════════════════════════════════════════════════
_NOISE_CLASS_FRAGMENTS: tuple[str, ...] = (
    "cookie", "banner", "popup", "modal", "overlay", "consent",
    "gdpr", "notification", "toast", "alert-bar",
    "login", "signin", "signup", "auth", "otp",
    "download", "app-download", "appdownload",
    "breadcrumb", "pagination", "pager",
    "footer", "navbar", "topbar", "sidebar",
)

# ═══════════════════════════════════════════════════════════════════════════
# 3. TEXT-LEVEL NOISE — regex blacklist applied to cleaned text
# ═══════════════════════════════════════════════════════════════════════════
_TEXT_JUNK_RE = re.compile(
    r"^("
    # Error / loading states
    r"we'?re sorry|page not found|404|error|something went wrong|loading\.{0,3}"
    # Pure UI labels
    r"|login|log in|sign up|sign in|register|download app|get the app"
    r"|view all|see all|show more|load more|back to top"
    # Bare SEO keyword phrases
    r"|near me|best services?|top services?|services? near me"
    r"|home services?|all services?"
    r")$",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# 4. SERVICE / CTA / PRICING CLASSIFIERS
# ═══════════════════════════════════════════════════════════════════════════
_SERVICE_RE = re.compile(
    r"\b(clean|cleaning|repair|fix|install|maintain|service|salon|beauty|"
    r"plumb|electr|pest|paint|massage|yoga|fitness|handyman|book|grooming|"
    r"spa|laundry|carpent|waterproof|polish|sanitiz|disinfect)\b",
    re.IGNORECASE,
)

_CTA_VERBS_RE = re.compile(
    r"\b(book now|book a|get started|schedule|hire|order|explore|view details|"
    r"check availability|get service|request|try now|start now|subscribe)\b",
    re.IGNORECASE,
)

_PRICING_RE = re.compile(
    r"(₹\s*\d[\d,]*"
    r"|\d+\s*%\s*off"
    r"|starting\s+(?:from\s+)?(?:at\s+)?₹"
    r"|from\s+₹"
    r"|\bflat\s+\d+"
    r"|\bdiscount\b"
    r"|\boffer\b"
    r"|\bpromo\b"
    r"|\bfree\b)",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# 5. SERVICE CARD / TILE DETECTION
# ═══════════════════════════════════════════════════════════════════════════
_CARD_CLASS_HINTS: tuple[str, ...] = (
    "card", "tile", "service", "category", "servicecategory",
    "service-card", "service-tile", "category-card",
    "category-item", "service-item", "product-card",
)

# ═══════════════════════════════════════════════════════════════════════════
# 6. QUALITY CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════
MIN_WORDS: int = 5
MAX_WORDS: int = 25
MAX_UPPERCASE_RATIO: float = 0.6   # discard if > 60 % chars are uppercase


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _is_noise_element(tag: Tag) -> bool:
    """Return True if element's class/id marks it as structural noise."""
    classes = " ".join(tag.get("class", [])).lower()
    element_id = (tag.get("id") or "").lower()
    combined = classes + " " + element_id
    return any(fragment in combined for fragment in _NOISE_CLASS_FRAGMENTS)


def _has_card_class(tag: Tag) -> bool:
    classes = " ".join(tag.get("class", [])).lower()
    return any(hint in classes for hint in _CARD_CLASS_HINTS)


def _get_raw_text(tag: Tag) -> str:
    """Return whitespace-normalised inner text of *tag* (no quality checks)."""
    return clean_text(tag.get_text(separator=" ", strip=True))


def _quality_check(text: str) -> bool:
    """
    Return True if *text* passes all quality gates.

    Gates
    -----
    1. Minimum word count (>= MIN_WORDS)
    2. Minimum meaningful (non-stop) word count (>= 2)
    3. Uppercase ratio <= MAX_UPPERCASE_RATIO
    4. Not a known junk phrase
    5. Not flagged by utils.is_noise()
    """
    if not text:
        return False

    words = text.split()

    # Gate 1 — minimum length
    if len(words) < MIN_WORDS:
        return False

    # Gate 2 — must have at least 2 alphabetic words of length > 2
    meaningful = [w for w in words if w.isalpha() and len(w) > 2]
    if len(meaningful) < 2:
        return False

    # Gate 3 — not predominantly uppercase (SEO keyword tables, nav labels)
    letters = [c for c in text if c.isalpha()]
    if letters:
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if upper_ratio > MAX_UPPERCASE_RATIO:
            return False

    # Gate 4 — not a known junk phrase
    if _TEXT_JUNK_RE.match(text.strip()):
        return False

    # Gate 5 — utils noise check
    if is_noise(text):
        return False

    return True


def _smart_label(text: str) -> str:
    """
    Assign a content_type based on text signals.

    Priority: cta > pricing > service > paragraph
    """
    if _CTA_VERBS_RE.search(text):
        return "cta"
    if _PRICING_RE.search(text):
        return "pricing"
    if _SERVICE_RE.search(text):
        return "service"
    return "paragraph"


def _normalize_for_dedup(text: str) -> str:
    """Lowercase + collapse whitespace for hash-stable comparison."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def _truncate_to_max_words(text: str, limit: int = MAX_WORDS) -> str:
    """Return the first *limit* words of *text*."""
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit])


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT EXPANSION
# ═══════════════════════════════════════════════════════════════════════════

def _expand_with_context(tag: Tag, base_text: str) -> str:
    """
    If *base_text* is short (< MIN_WORDS), try to enrich it with text from:
    1. The immediately following sibling <p> or <span>
    2. The parent container's own direct-child text nodes

    Returns the (possibly expanded) text, still within MAX_WORDS.
    """
    if len(base_text.split()) >= MIN_WORDS:
        return base_text

    candidates: list[str] = []

    # Look for next sibling paragraph / span
    sibling = tag.find_next_sibling(["p", "span", "div"])
    if sibling and not _is_noise_element(sibling):
        sib_text = _get_raw_text(sibling)
        if sib_text:
            candidates.append(sib_text)

    # Look at parent's own direct text (excluding our tag's text)
    parent = tag.parent
    if parent and not _is_noise_element(parent):
        parent_direct = " ".join(
            str(child).strip()
            for child in parent.children
            if isinstance(child, NavigableString) and str(child).strip()
        )
        parent_direct = clean_text(parent_direct)
        if parent_direct:
            candidates.append(parent_direct)

    combined = base_text
    for extra in candidates:
        trial = f"{combined} {extra}"
        trial_words = trial.split()
        if len(trial_words) >= MIN_WORDS:
            combined = " ".join(trial_words[:MAX_WORDS])
            break

    return combined


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTION PASSES
# ═══════════════════════════════════════════════════════════════════════════

def _extract_headlines(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    h1 / h2 / h3 → try to merge with immediately following sibling <p>
    to create richer semantic units.
    """
    results: list[tuple[str, str]] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        if _is_noise_element(tag):
            continue
        base = _get_raw_text(tag)
        if not base:
            continue

        # Try to merge with the following sibling paragraph for context
        next_p = tag.find_next_sibling("p")
        if next_p and not _is_noise_element(next_p):
            sibling_text = _get_raw_text(next_p)
            if sibling_text:
                merged = f"{base} — {sibling_text}"
                merged_words = merged.split()
                if len(merged_words) <= MAX_WORDS:
                    base = merged
                else:
                    base = " ".join(merged_words[:MAX_WORDS])

        # If still short, try parent-context expansion
        base = _expand_with_context(tag, base)

        text = _truncate_to_max_words(base)
        if _quality_check(text):
            label = _smart_label(text)
            print(f"[PARSER] Cleaned chunk: [{label}] {text!r}")
            results.append((label, text))

    return results


def _extract_paragraphs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """<p> tags — quality-filtered, smart-labelled."""
    results: list[tuple[str, str]] = []
    for tag in soup.find_all("p"):
        if _is_noise_element(tag):
            continue
        text = _truncate_to_max_words(_get_raw_text(tag))
        if _quality_check(text):
            label = _smart_label(text)
            print(f"[PARSER] Cleaned chunk: [{label}] {text!r}")
            results.append((label, text))
    return results


def _extract_ctas(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    <button> and CTA-styled / CTA-keyword <a> elements.
    CTAs must pass word-count gate and the CTA verb check.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add_cta(text: str) -> None:
        norm = _normalize_for_dedup(text)
        if norm in seen:
            return
        # CTAs are allowed to be shorter than general content but need CTA verb
        if len(text.split()) < 2:
            return
        if _TEXT_JUNK_RE.match(text.strip()):
            return
        if not _CTA_VERBS_RE.search(text):
            return
        seen.add(norm)
        print(f"[PARSER] Cleaned chunk: [cta] {text!r}")
        results.append(("cta", text))

    for tag in soup.find_all("button"):
        if _is_noise_element(tag):
            continue
        text = _get_raw_text(tag)
        if text:
            _add_cta(text)

    for tag in soup.find_all("a"):
        if _is_noise_element(tag):
            continue
        role = (tag.get("role") or "").lower()
        classes = " ".join(tag.get("class", [])).lower()
        text = _get_raw_text(tag)
        if not text:
            continue
        is_styled = role == "button" or any(
            c in classes for c in ("btn", "cta", "button", "action", "book")
        )
        is_keyword = bool(_CTA_VERBS_RE.search(text))
        if is_styled or is_keyword:
            _add_cta(text)

    return results


def _extract_service_cards(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    Service card / tile containers → 'service'.

    Strategy: collect the direct visible text of the card PLUS the text of
    its first <p> or <span> child (context expansion). This avoids pulling
    in deeply nested, unrelated content yet still enriches bare title labels.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for tag in soup.find_all(["div", "section", "article", "li"]):
        if not _has_card_class(tag):
            continue
        if _is_noise_element(tag):
            continue

        # Only look at the immediate text content (not full subtree) to avoid
        # duplicating content grabbed by other extractors.
        direct_text = clean_text(
            " ".join(
                str(c).strip()
                for c in tag.children
                if isinstance(c, NavigableString) and str(c).strip()
            )
        )

        # Fallback: heading inside card
        heading = tag.find(["h2", "h3", "h4", "strong"])
        heading_text = _get_raw_text(heading) if heading else ""

        base = direct_text or heading_text
        if not base:
            base = _get_raw_text(tag)

        # Try to merge a child <p> for richer context
        child_p = tag.find("p")
        if child_p and not _is_noise_element(child_p):
            child_text = _get_raw_text(child_p)
            if child_text:
                combined = f"{base} {child_text}".strip()
                base = " ".join(combined.split()[:MAX_WORDS])

        # Context expand if still short
        base = _expand_with_context(tag, base)
        text = _truncate_to_max_words(base)

        norm = _normalize_for_dedup(text)
        if _quality_check(text) and norm not in seen:
            seen.add(norm)
            label = _smart_label(text)
            print(f"[PARSER] Cleaned chunk: [{label}] {text!r}")
            results.append((label, text))

    return results


def _extract_pricing(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Leaf-level elements containing pricing / offer signals → 'pricing'."""
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for tag in soup.find_all(["span", "div", "p", "li", "strong", "em", "b"]):
        if _is_noise_element(tag):
            continue
        if len(tag.find_all(recursive=False)) > 3:
            continue  # too deep — avoid pulling in entire sections
        text = _truncate_to_max_words(_get_raw_text(tag))
        norm = _normalize_for_dedup(text)
        if (
            text
            and _PRICING_RE.search(text)
            and norm not in seen
            and _quality_check(text)
        ):
            seen.add(norm)
            print(f"[PARSER] Cleaned chunk: [pricing] {text!r}")
            results.append(("pricing", text))

    return results


def _extract_lists(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    <li> items from meaningful lists.
    Short list items are expanded with their parent list's descriptor.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()

    for ul_ol in soup.find_all(["ul", "ol"]):
        if _is_noise_element(ul_ol):
            continue

        # Try to get a label for the whole list (preceding heading / aria-label)
        list_label = ""
        prev = ul_ol.find_previous_sibling(["h2", "h3", "h4", "p"])
        if prev:
            list_label = _get_raw_text(prev)
            if len(list_label.split()) > 6:
                list_label = ""   # too long to use as prefix

        for li in ul_ol.find_all("li", recursive=False):
            if _is_noise_element(li):
                continue
            base = _get_raw_text(li)
            # If short, prepend list label for context
            if base and list_label and len(base.split()) < MIN_WORDS:
                base = f"{list_label}: {base}"
            base = _expand_with_context(li, base)
            text = _truncate_to_max_words(base)
            norm = _normalize_for_dedup(text)
            if _quality_check(text) and norm not in seen:
                seen.add(norm)
                label = _smart_label(text)
                print(f"[PARSER] Cleaned chunk: [{label}] {text!r}")
                results.append((label, text))

    return results


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API  (interface unchanged)
# ═══════════════════════════════════════════════════════════════════════════

def parse_page(html: str) -> list[tuple[str, str]]:
    """
    Parse *html* and return high-quality (content_type, text) pairs.

    Parameters
    ----------
    html : str
        Raw HTML source of the page (post-JS-render from Playwright).

    Returns
    -------
    list of (content_type, text) tuples where content_type ∈
        { "headline", "service", "paragraph", "cta", "pricing", "list_item" }

    Quality guarantees per item
    ---------------------------
    * 5–25 words
    * At least 2 meaningful alphabetic words
    * Not predominantly uppercase
    * Not a known junk / error / nav phrase
    * Context-expanded when short (merged with sibling/parent text)
    * Globally deduped via normalised string comparison within this parse call
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── Pass 0: Remove structural noise subtrees ──────────────────────────
    for tag in soup.find_all(list(_IGNORED_TAGS)):
        tag.decompose()

    # ── Pass 1: Extract by element type ───────────────────────────────────
    raw: list[tuple[str, str]] = []
    raw.extend(_extract_headlines(soup))
    raw.extend(_extract_service_cards(soup))
    raw.extend(_extract_paragraphs(soup))
    raw.extend(_extract_pricing(soup))
    raw.extend(_extract_ctas(soup))
    raw.extend(_extract_lists(soup))

    # ── Pass 2: Global deduplication across all extraction types ──────────
    final: list[tuple[str, str]] = []
    global_seen: set[str] = set()
    for content_type, text in raw:
        norm = _normalize_for_dedup(text)
        if norm not in global_seen:
            global_seen.add(norm)
            final.append((content_type, text))

    logger.info(
        "[parser] Extracted %d items → %d after global dedup  (dropped %d duplicates)",
        len(raw), len(final), len(raw) - len(final),
    )
    return final
