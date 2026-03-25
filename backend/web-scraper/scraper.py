"""
scraper.py
----------
Playwright-based scraping layer with concurrency and retry support.

Responsibilities
----------------
* scrape_url()        – scrape a single URL, return raw HTML (with retry)
* scrape_batch()      – scrape a list of URLs concurrently (max 5 workers)
* _run_page()         – low-level Playwright page interaction

Design notes
------------
* One shared Playwright Browser instance per batch run (headless Chromium).
* Each concurrent task gets its own BrowserContext + Page for isolation.
* asyncio.Semaphore limits live contexts to MAX_CONCURRENT_TASKS.
* Retry up to MAX_RETRIES times on any exception; logs each failure.
* Returns None for a URL that exhausts all retries (pipeline continues).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    async_playwright,
)

from config import MAX_CONCURRENT_TASKS, MAX_RETRIES, PAGE_TIMEOUT_MS, POST_LOAD_DELAY_MS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level page fetch
# ---------------------------------------------------------------------------

async def _run_page(context: BrowserContext, url: str) -> str:
    """
    Open *url* in a new page within *context* and return the final HTML.

    Waits for `networkidle` so JavaScript-rendered content is fully loaded,
    then sleeps POST_LOAD_DELAY_MS extra milliseconds to let SPA frameworks
    (e.g. React, Next.js) finish client-side hydration and lazy-load content.
    """
    page: Page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=PAGE_TIMEOUT_MS)
        # Extra delay for JS-heavy sites like Urban Company
        if POST_LOAD_DELAY_MS > 0:
            await page.wait_for_timeout(POST_LOAD_DELAY_MS)
        html = await page.content()
        return html
    finally:
        await page.close()


# ---------------------------------------------------------------------------
# Single-URL scrape with retry
# ---------------------------------------------------------------------------

async def scrape_url(
    browser: Browser,
    url: str,
    retries: int = MAX_RETRIES,
) -> Optional[str]:
    """
    Scrape *url* and return raw HTML, or None after exhausting *retries*.

    Each attempt uses a fresh BrowserContext so cookies/state don't bleed
    between attempts.
    """
    for attempt in range(1, retries + 2):  # attempts = retries + 1 initial
        context: Optional[BrowserContext] = None
        try:
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                java_script_enabled=True,
                ignore_https_errors=True,
            )
            html = await _run_page(context, url)
            logger.info("Scraped %s (attempt %d).", url, attempt)
            return html
        except Exception as exc:
            logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt, retries + 1, url, exc,
            )
            if attempt > retries:
                logger.error("All retries exhausted for %s. Skipping.", url)
                return None
        finally:
            if context:
                await context.close()

    return None  # unreachable but satisfies type checkers


# ---------------------------------------------------------------------------
# Concurrent batch scraper
# ---------------------------------------------------------------------------

async def scrape_batch(urls: list[str]) -> dict[str, Optional[str]]:
    """
    Scrape all *urls* concurrently, capped at MAX_CONCURRENT_TASKS.

    Returns
    -------
    dict mapping url → html string (or None on failure).
    """
    results: dict[str, Optional[str]] = {}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    async def bounded_scrape(browser: Browser, url: str) -> None:
        async with semaphore:
            results[url] = await scrape_url(browser, url)

    async with async_playwright() as pw:
        browser: Browser = await pw.chromium.launch(headless=True)
        try:
            tasks = [
                asyncio.create_task(bounded_scrape(browser, url))
                for url in urls
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await browser.close()

    return results
