"""
scheduler.py
------------
State-based 24-hour scheduler for the competitive intelligence scraper.

Debug additions
---------------
* Full per-stage INFO/DEBUG logging (scheduler start, URL selection,
  scrape start/end, parse preview, chunk counts, DB insert counts).
* scrape_state decision logging (SCRAPE / SKIP + timestamps).
* Test mode: --test flag runs ONE URL, forces scraping, no concurrency.
* DB connection verified at startup (verify_connection + check_tables_exist).
* All exceptions print full stack traces.

Usage
-----
Normal:   python scheduler.py
Test:     python scheduler.py --test [optional-url]
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from datetime import datetime
from typing import Optional

import db
from config import (
    COMPETITORS,
    CHUNK_MAX_WORDS,
    CHUNK_MIN_WORDS,
    FORCE_SCRAPE,
    SCRAPE_INTERVAL_HOURS,
    SCHEDULER_POLL_INTERVAL_SECONDS,
)
from parser import parse_page
from scraper import scrape_batch, scrape_url
from utils import chunk_text, compute_hash, normalize_url

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# URL → competitor_id index
# ---------------------------------------------------------------------------

def _build_url_map() -> dict[str, dict]:
    """
    Returns a flat dict:  normalised_url → {"competitor_id": int, "name": str}

    All URLs are normalised via normalize_url() at registration time so the
    rest of the pipeline always operates on canonical URL strings.
    Upserts competitor rows into the DB as a side effect.
    """
    url_map: dict[str, dict] = {}
    for comp in COMPETITORS:
        logger.debug("[scheduler] Upserting competitor: %s (%s)", comp["name"], comp["domain"])
        comp_id = db.upsert_competitor(comp["name"], comp["domain"])
        for raw_url in comp["urls"]:
            canonical = normalize_url(raw_url)
            url_map[canonical] = {"competitor_id": comp_id, "name": comp["name"]}
            logger.debug(
                "[scheduler]   Registered URL: %s  (comp_id=%d)", canonical, comp_id
            )
    return url_map


# ---------------------------------------------------------------------------
# Single-URL pipeline
# ---------------------------------------------------------------------------

def _process_html(
    url: str,
    html: str,
    competitor_id: int,
    scraped_at: datetime,
) -> None:
    """
    Full pipeline for one successfully scraped URL:
    parse → chunk → deduplicate → store → update scrape_state.
    """
    logger.info("[pipeline:%s] ── Stage 1: HTML received  (len=%d chars)", url, len(html))

    # ── Stage 1: Create snapshot ──────────────────────────────────────────
    logger.info("[pipeline:%s] ── Stage 2: Creating snapshot in DB …", url)
    snapshot_id = db.create_snapshot(competitor_id, url)
    logger.info("[pipeline:%s]    snapshot_id = %d", url, snapshot_id)

    # ── Stage 2: Parse HTML ───────────────────────────────────────────────
    logger.info("[pipeline:%s] ── Stage 3: Parsing HTML with BeautifulSoup …", url)
    content_items = parse_page(html)
    logger.info("[pipeline:%s]    Parser returned %d content items.", url, len(content_items))

    if not content_items:
        logger.warning(
            "[pipeline:%s]    ⚠ Parser returned EMPTY output. "
            "HTML may be entirely JS-rendered or page structure changed. "
            "Check POST_LOAD_DELAY_MS and parser noise filters.",
            url,
        )

    # ── Stage 3: Chunk + hash + store ─────────────────────────────────────
    logger.info("[pipeline:%s] ── Stage 4: Chunking + deduplication + insert …", url)

    total_chunks = 0
    inserted = 0
    skipped = 0
    preview_shown = 0

    for content_type, text in content_items:
        chunks = chunk_text(text, min_words=CHUNK_MIN_WORDS, max_words=CHUNK_MAX_WORDS)
        total_chunks += len(chunks)

        for chunk in chunks:
            # Show first 5 chunks as preview
            if preview_shown < 5:
                logger.info(
                    "[pipeline:%s]    CHUNK PREVIEW [%s]: %r",
                    url, content_type, chunk,
                )
                preview_shown += 1

            h = compute_hash(chunk)
            ok = db.insert_content_chunk(snapshot_id, content_type, chunk, h)
            if ok:
                inserted += 1
            else:
                skipped += 1

    logger.info(
        "[pipeline:%s] ── Stage 4 done: total_chunks=%d  inserted=%d  duplicates_skipped=%d",
        url, total_chunks, inserted, skipped,
    )

    if total_chunks == 0:
        logger.warning(
            "[pipeline:%s]    ⚠ No chunks produced. Parser items exist (%d) "
            "but all were too short (< %d words) or only noise.",
            url, len(content_items), CHUNK_MIN_WORDS,
        )

    # ── Stage 4: Update scrape_state ─────────────────────────────────────
    logger.info("[pipeline:%s] ── Stage 5: Updating scrape_state …", url)
    db.update_scrape_state(url)
    logger.info("[pipeline:%s] ── Pipeline complete ✓", url)


# ---------------------------------------------------------------------------
# Batch cycle
# ---------------------------------------------------------------------------

async def run_cycle(url_map: dict[str, dict], force: bool = False) -> None:
    """
    One full scraping cycle.

    Parameters
    ----------
    force : bool
        If True bypass the 24h gate and scrape every URL.  Driven by
        config.FORCE_SCRAPE or the --test CLI flag.
    """
    all_urls = list(url_map.keys())
    logger.info("[cycle] Total tracked URLs: %d", len(all_urls))

    due_urls = db.get_all_due_urls(all_urls, SCRAPE_INTERVAL_HOURS, force=force)
    logger.info("[cycle] URLs due for scraping: %d", len(due_urls))

    if not due_urls:
        logger.info("[cycle] No URLs are due. Exiting cycle.")
        return

    # Scrape concurrently
    scraped_at = datetime.utcnow()
    logger.info("[cycle] ── Scrape batch START  (%d URLs) …", len(due_urls))
    results = await scrape_batch(due_urls)
    logger.info("[cycle] ── Scrape batch END.")

    success_count = sum(1 for v in results.values() if v is not None)
    fail_count = len(results) - success_count
    logger.info("[cycle]    Scraped OK: %d  Failed: %d", success_count, fail_count)

    for url, html in results.items():
        print(f"[SCRAPER] Processing URL: {url}")
        if html is None:
            logger.error("[cycle] ✗ Skipping %s — scrape returned None after all retries.", url)
            continue

        comp_info = url_map[url]
        logger.info("[cycle] → Running pipeline for: %s", url)
        try:
            _process_html(url, html, comp_info["competitor_id"], scraped_at)
        except Exception:
            logger.error(
                "[cycle] ✗ Pipeline error for %s:\n%s", url, traceback.format_exc()
            )


# ---------------------------------------------------------------------------
# Test mode — single URL, sequential, force-scraped
# ---------------------------------------------------------------------------

async def run_test_mode(url_map: dict[str, dict], test_url: Optional[str] = None) -> None:
    """
    Test mode: scrape ONE URL (first in list or specified), bypass 24h gate,
    run sequentially (no concurrency), print full trace.
    """
    if test_url and test_url in url_map:
        url = test_url
    elif test_url:
        logger.error("[test] URL '%s' is not in the configured URL map.", test_url)
        logger.error("[test] Known URLs:\n  %s", "\n  ".join(url_map.keys()))
        return
    else:
        url = next(iter(url_map))  # first configured URL

    comp_info = url_map[url]
    logger.info("=" * 70)
    logger.info("[test] TEST MODE — single URL, no concurrency, force-scrape")
    logger.info("[test] Target URL : %s", url)
    logger.info("[test] Competitor : %s (id=%d)", comp_info["name"], comp_info["competitor_id"])
    logger.info("=" * 70)

    # ── DB health checks ─────────────────────────────────────────────────
    logger.info("[test] ── Step 0a: Verifying DB connection …")
    ok = db.verify_connection()
    if not ok:
        logger.error("[test] DB connection failed — aborting test.")
        return

    logger.info("[test] ── Step 0b: Checking table existence …")
    db.check_tables_exist()

    # ── Scrape ───────────────────────────────────────────────────────────
    logger.info("[test] ── Step 1: Scraping URL (sequential, no semaphore) …")
    from playwright.async_api import async_playwright  # local import to keep module clean
    html: Optional[str] = None
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            html = await scrape_url(browser, url)
        finally:
            await browser.close()

    if html is None:
        logger.error("[test] ✗ Scraper returned None — page could not be fetched.")
        logger.error(
            "[test]   Possible causes:\n"
            "   • Network/firewall blocking Playwright\n"
            "   • PAGE_TIMEOUT_MS (%s ms) too low\n"
            "   • URL returns 4xx/5xx",
            "see config.py",
        )
        return

    logger.info("[test] ✓ HTML received  (%d chars)", len(html))

    # ── Parse ─────────────────────────────────────────────────────────────
    logger.info("[test] ── Step 2: Parsing HTML …")
    content_items = parse_page(html)
    logger.info("[test]    Parser returned %d items.", len(content_items))

    if not content_items:
        logger.warning(
            "[test]   ⚠ Parser returned EMPTY output.\n"
            "   Possible causes:\n"
            "   • Page is entirely client-rendered (try increasing POST_LOAD_DELAY_MS)\n"
            "   • All content filtered as noise (review _NOISE_CLASS_FRAGMENTS in parser.py)\n"
            "   • Page requires login/geo-block before content loads"
        )
    else:
        logger.info("[test]   First 5 parsed items:")
        for i, (ctype, text) in enumerate(content_items[:5]):
            logger.info("[test]     %d. [%s] %r", i + 1, ctype, text[:120])

    # ── Chunk ─────────────────────────────────────────────────────────────
    logger.info("[test] ── Step 3: Chunking …")
    all_chunks: list[tuple[str, str]] = []
    for ctype, text in content_items:
        for chunk in chunk_text(text, min_words=CHUNK_MIN_WORDS, max_words=CHUNK_MAX_WORDS):
            all_chunks.append((ctype, chunk))

    logger.info("[test]    Total chunks produced: %d", len(all_chunks))
    if all_chunks:
        logger.info("[test]   First 5 chunks:")
        for i, (ctype, chunk) in enumerate(all_chunks[:5]):
            logger.info("[test]     %d. [%s] %r", i + 1, ctype, chunk)
    else:
        logger.warning(
            "[test]   ⚠ 0 chunks produced even though parser returned %d items.\n"
            "   Possible cause: all extracted text is shorter than %d words.",
            len(content_items), CHUNK_MIN_WORDS,
        )

    # ── DB insert ──────────────────────────────────────────────────────────
    logger.info("[test] ── Step 4: Inserting into DB …")
    scraped_at = datetime.utcnow()
    try:
        snapshot_id = db.create_snapshot(comp_info["competitor_id"], url)
        inserted = 0
        for ctype, chunk in all_chunks:
            h = compute_hash(chunk)
            if db.insert_content_chunk(snapshot_id, ctype, chunk, h):
                inserted += 1
        db.update_scrape_state(url, scraped_at)
        logger.info("[test]    ✓ %d / %d chunks inserted into extracted_content.", inserted, len(all_chunks))
    except Exception:
        logger.error("[test]   ✗ DB insert failed:\n%s", traceback.format_exc())
        return

    logger.info("=" * 70)
    logger.info("[test] TEST COMPLETE  snapshot_id=%d  inserted=%d", snapshot_id, inserted)
    logger.info("=" * 70)


# ---------------------------------------------------------------------------
# Scheduler main loop
# ---------------------------------------------------------------------------

async def _scheduler_loop(url_map: dict[str, dict]) -> None:
    logger.info(
        "[scheduler] Loop started. Poll interval: %ds, Scrape interval: %dh.",
        SCHEDULER_POLL_INTERVAL_SECONDS, SCRAPE_INTERVAL_HOURS,
    )
    while True:
        logger.info("[scheduler] ═══ Cycle start  %s ═══", datetime.utcnow().isoformat())
        try:
            await run_cycle(url_map, force=FORCE_SCRAPE)
        except Exception:
            logger.error("[scheduler] Unhandled cycle error:\n%s", traceback.format_exc())

        logger.info(
            "[scheduler] ═══ Cycle end. Sleeping %ds ═══",
            SCHEDULER_POLL_INTERVAL_SECONDS,
        )
        await asyncio.sleep(SCHEDULER_POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,        # DEBUG so all pipeline stages are visible
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quieten noisy third-party loggers
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def start_scheduler() -> None:
    """Normal entry point — runs the full continuous scheduler."""
    _setup_logging()

    logger.info("[startup] ── Verifying DB connection …")
    if not db.verify_connection():
        logger.error("[startup] Cannot connect to DB — aborting.")
        sys.exit(1)

    logger.info("[startup] ── Checking tables …")
    db.check_tables_exist()

    logger.info("[startup] ── Initialising DB schema …")
    db.init_db()

    logger.info("[startup] ── Building competitor URL map …")
    url_map = _build_url_map()
    logger.info(
        "[startup] Tracking %d URLs across %d competitors.",
        len(url_map), len(COMPETITORS),
    )

    asyncio.run(_scheduler_loop(url_map))


if __name__ == "__main__":
    _setup_logging()

    # ── Test mode ────────────────────────────────────────────────────────
    if "--test" in sys.argv:
        # Optionally pass a specific URL after --test
        idx = sys.argv.index("--test")
        explicit_url: Optional[str] = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None

        logger.info("[startup] ── Initialising DB schema …")
        db.init_db()

        logger.info("[startup] ── Building competitor URL map …")
        url_map = _build_url_map()

        asyncio.run(run_test_mode(url_map, test_url=explicit_url))

    # ── Normal scheduler mode ────────────────────────────────────────────
    else:
        start_scheduler()
