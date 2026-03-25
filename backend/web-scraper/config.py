"""
config.py
---------
Central configuration for the competitive intelligence scraper.
Loads environment variables and defines competitor/URL data + runtime constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
"""
Expected format (Neon / standard PostgreSQL):
  postgresql://user:password@host:port/dbname?sslmode=require
"""

# ---------------------------------------------------------------------------
# Scraper runtime constants
# ---------------------------------------------------------------------------
SCRAPE_INTERVAL_HOURS: int = 24          # How often each URL is re-scraped
MAX_CONCURRENT_TASKS: int = 5            # Max parallel Playwright contexts
MAX_RETRIES: int = 2                     # Retry attempts per URL on failure
PAGE_TIMEOUT_MS: int = 30_000           # Playwright page load timeout (ms)
POST_LOAD_DELAY_MS: int = 2_500         # Extra wait after networkidle (JS-heavy SPAs)
SCHEDULER_POLL_INTERVAL_SECONDS: int = 300  # How often scheduler checks for due URLs

# ---------------------------------------------------------------------------
# Chunking constraints
# ---------------------------------------------------------------------------
CHUNK_MIN_WORDS: int = 5
CHUNK_MAX_WORDS: int = 30

# ---------------------------------------------------------------------------
# Competitor / URL definitions
# ---------------------------------------------------------------------------
# RULES (strict — do not break these):
#   • Only list URLs you explicitly trust and want scraped.
#   • Do NOT add placeholder / example domains.
#   • The scraper will never discover, crawl, or generate URLs at runtime.
#   • If fewer URLs exist than expected, the system processes what is here —
#     it will NOT auto-fill or pad the list.
#
# Structure:
#   {
#       "name": str,    – human-readable competitor name
#       "domain": str,  – root domain (stored in the `competitors` table)
#       "urls": list[str],  – explicit pages to monitor (no wildcards)
#   }

COMPETITORS: list[dict] = [
    {
        "name": "Urban Company",
        "domain": "www.urbancompany.com",
        "urls": [
            "https://www.urbancompany.com/",
            "https://www.urbancompany.com/chennai",
            "https://www.urbancompany.com/services",
            "https://www.urbancompany.com/chennai/home-cleaning",
        ],
    },
    # Add real competitors here. Remove this comment block when you do.
    # {
    #     "name": "Another Competitor",
    #     "domain": "www.example-competitor.com",
    #     "urls": [
    #         "https://www.example-competitor.com/",
    #         "https://www.example-competitor.com/pricing",
    #     ],
    # },
]

