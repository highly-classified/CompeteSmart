"""
db.py
-----
PostgreSQL data layer (psycopg2, no ORM).

Debug additions
---------------
* verify_connection()     – SELECT NOW() + SSL check, logs result
* check_tables_exist()    – verifies all required tables are present
* create_snapshot()       – logs snapshot_id after insert
* insert_content_chunk()  – logs row-count before/after, full traceback on error
"""

from __future__ import annotations

import logging
import traceback
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

from config import DATABASE_URL
from utils import normalize_url

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection pool (1–10 connections)
# ---------------------------------------------------------------------------
_pool: Optional[ThreadedConnectionPool] = None

_REQUIRED_TABLES = [
    "competitors",
    "snapshots",
    "extracted_content",
    "scrape_state",
]


def get_pool() -> ThreadedConnectionPool:
    """Return the module-level connection pool, creating it on first call."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is empty. Check your .env file and ensure "
                "python-dotenv loaded it before importing db."
            )
        logger.debug("[DB] Creating connection pool with DSN: %s…", DATABASE_URL[:40])
        _pool = ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
        logger.info("[DB] Connection pool created successfully.")
    return _pool


@contextmanager
def get_conn() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager that borrows a connection from the pool and returns it."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
        logger.debug("[DB] Transaction committed.")
    except Exception:
        conn.rollback()
        logger.debug("[DB] Transaction rolled back due to exception.")
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

def verify_connection() -> bool:
    """
    Run SELECT NOW() to confirm the DB is reachable and log the server time.
    Also logs the SSL status of the connection.

    Returns True on success, False on failure.
    """
    logger.info("[DB:verify] Testing database connection …")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT NOW(), version()")
                row = cur.fetchone()
                logger.info("[DB:verify] ✓ Connected. Server time: %s", row[0])
                logger.info("[DB:verify]   PostgreSQL version: %s", row[1][:60])

                # Check SSL
                cur.execute(
                    "SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()"
                )
                ssl_row = cur.fetchone()
                if ssl_row:
                    logger.info(
                        "[DB:verify]   SSL active: %s | SSL version: %s",
                        ssl_row[0], ssl_row[1],
                    )
                else:
                    logger.warning(
                        "[DB:verify]   Could not determine SSL status "
                        "(pg_stat_ssl returned no row for this connection)."
                    )
        return True
    except Exception as exc:
        logger.error("[DB:verify] ✗ Connection FAILED: %s", exc)
        logger.error(traceback.format_exc())
        return False


def check_tables_exist() -> bool:
    """
    Verify all required tables exist in the public schema.
    Logs a warning for each missing table.
    Returns True only if ALL tables are present.
    """
    logger.info("[DB:tables] Checking for required tables …")
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(%s)
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (_REQUIRED_TABLES,))
                found = {row[0] for row in cur.fetchall()}

        missing = [t for t in _REQUIRED_TABLES if t not in found]
        for t in _REQUIRED_TABLES:
            status = "✓" if t in found else "✗ MISSING"
            logger.info("[DB:tables]   %s  %s", status, t)

        if missing:
            logger.warning(
                "[DB:tables] Missing tables: %s — run init_db() to create them.",
                missing,
            )
            return False

        logger.info("[DB:tables] All required tables present.")
        return True
    except Exception as exc:
        logger.error("[DB:tables] Could not check tables: %s", exc)
        logger.error(traceback.format_exc())
        return False


def _get_row_count(cur: psycopg2.extensions.cursor, table: str) -> int:
    """Return the approximate row count for *table*."""
    cur.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
    return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------
_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS competitors (
    id     SERIAL PRIMARY KEY,
    name   TEXT NOT NULL,
    domain TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id             SERIAL PRIMARY KEY,
    competitor_id  INT  NOT NULL REFERENCES competitors(id),
    url            TEXT NOT NULL,
    is_synthetic   BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extracted_content (
    id           SERIAL PRIMARY KEY,
    snapshot_id  INT  NOT NULL REFERENCES snapshots(id),
    content_type TEXT NOT NULL,
    content      TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    is_synthetic BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_state (
    url             TEXT PRIMARY KEY,
    last_scraped_at TIMESTAMP NOT NULL
);
"""


def init_db() -> None:
    """Create all tables if they do not yet exist (idempotent)."""
    logger.info("[DB:init] Running CREATE TABLE IF NOT EXISTS for all tables …")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # 1. Create tables if not exists
                cur.execute(_CREATE_TABLES_SQL)

                # 2. Light migration: ensure 'is_synthetic' column exists
                # (Handles cases where tables were created before this feature)
                cur.execute("ALTER TABLE snapshots ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN DEFAULT FALSE")
                cur.execute("ALTER TABLE extracted_content ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN DEFAULT FALSE")

        logger.info("[DB:init] ✓ Schema initialised.")
    except Exception as exc:
        logger.error("[DB:init] ✗ Schema init failed: %s", exc)
        logger.error(traceback.format_exc())
        raise


# ---------------------------------------------------------------------------
# competitors table
# ---------------------------------------------------------------------------

def upsert_competitor(name: str, domain: str) -> int:
    """
    Insert a competitor row if it doesn't exist; return its id either way.
    Uses (domain) as the natural unique key.
    """
    sql_select = "SELECT id FROM competitors WHERE domain = %s"
    sql_insert = "INSERT INTO competitors (name, domain) VALUES (%s, %s) RETURNING id"

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_select, (domain,))
                row = cur.fetchone()
                if row:
                    logger.debug("[DB:competitor] Existing id=%d for domain=%s", row[0], domain)
                    return row[0]
                cur.execute(sql_insert, (name, domain))
                new_id = cur.fetchone()[0]
                logger.info("[DB:competitor] Inserted new competitor id=%d  name=%s", new_id, name)
                return new_id
    except Exception as exc:
        logger.error("[DB:competitor] upsert_competitor failed for domain=%s: %s", domain, exc)
        logger.error(traceback.format_exc())
        raise


# ---------------------------------------------------------------------------
# snapshots table
# ---------------------------------------------------------------------------

def create_snapshot(
    competitor_id: int,
    url: str,
    is_synthetic: bool = False,
    created_at: Optional[datetime] = None,
) -> int:
    """Insert a new snapshot row and return its id."""
    sql = """
        INSERT INTO snapshots (competitor_id, url, is_synthetic, created_at)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """
    # Use provided created_at or default to NOW()
    ts = created_at or datetime.utcnow()

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                before = _get_row_count(cur, "snapshots")
                cur.execute(sql, (competitor_id, url, is_synthetic, ts))
                snapshot_id = cur.fetchone()[0]
                after = _get_row_count(cur, "snapshots")
                logger.info(
                    "[DB:snapshot] ✓ Created snapshot id=%d for url=%s "
                    "(snapshots: %d → %d, synthetic=%s)",
                    snapshot_id, url, before, after, is_synthetic,
                )
                return snapshot_id
    except Exception as exc:
        logger.error(
            "[DB:snapshot] ✗ create_snapshot FAILED for url=%s competitor_id=%d: %s",
            url, competitor_id, exc,
        )
        logger.error(traceback.format_exc())
        raise


# ---------------------------------------------------------------------------
# extracted_content table
# ---------------------------------------------------------------------------

def insert_content_chunk(
    snapshot_id: int,
    content_type: str,
    content: str,
    content_hash: str,
    is_synthetic: bool = False,
    created_at: Optional[datetime] = None,
) -> bool:
    """
    Insert a semantic chunk.

    Returns
    -------
    True  – inserted successfully
    False – duplicate hash (skipped)
    """
    sql = """
        INSERT INTO extracted_content (
            snapshot_id, content_type, content, content_hash, is_synthetic, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
    """
    ts = created_at or datetime.utcnow()

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (snapshot_id, content_type, content, content_hash, is_synthetic, ts),
                )
                inserted = cur.rowcount == 1
                if inserted:
                    logger.debug("[DB:content] Inserted chunk for snapshot_id=%d", snapshot_id)
                else:
                    logger.debug(
                        "[DB:chunk] ~ Duplicate skipped hash=%s…", content_hash[:12]
                    )
                return inserted
    except Exception as exc:
        logger.error(
            "[DB:chunk] ✗ insert_content_chunk FAILED snapshot_id=%d hash=%s: %s",
            snapshot_id, content_hash[:12], exc,
        )
        logger.error(traceback.format_exc())
        return False



# ---------------------------------------------------------------------------
# scrape_state table
# ---------------------------------------------------------------------------

def get_last_scraped_at(url: str) -> Optional[datetime]:
    """Return the last_scraped_at timestamp for the normalised *url*, or None."""
    url = normalize_url(url)
    sql = "SELECT last_scraped_at FROM scrape_state WHERE url = %s"
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (url,))
            row = cur.fetchone()
            return row[0] if row else None


def update_scrape_state(url: str) -> None:
    """
    Upsert the last_scraped_at for the normalised *url* using DB server time.
    """
    url = normalize_url(url)
    sql = """
        INSERT INTO scrape_state (url, last_scraped_at)
        VALUES (%s, NOW())
        ON CONFLICT (url)
        DO UPDATE SET last_scraped_at = NOW()
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (url,))
        logger.info("[DB:state] scrape_state updated (UPSERT) for url=%s", url)
    except Exception as exc:
        logger.error("[DB:state] update_scrape_state FAILED for url=%s: %s", url, exc)
        logger.error(traceback.format_exc())
        raise


def get_all_due_urls(
    all_urls: list[str],
    interval_hours: int,
    force: bool = False,
) -> list[str]:
    """
    Return the subset of *all_urls* that are due for scraping right now.

    Every URL is normalised before comparison so trailing-slash variants
    are treated identically.

    Parameters
    ----------
    force : bool
        If True, return ALL urls regardless of last_scraped_at.
        Driven by config.FORCE_SCRAPE or the --test CLI flag.

    Fail-safe
    ---------
    If the scrape_state lookup itself fails, default to scraping everything
    so a temporary DB connectivity hiccup never silently halts ingestion.
    """
    if not all_urls:
        return []

    # Normalise every incoming URL before any DB interaction
    normalised_urls = [normalize_url(u) for u in all_urls]

    if force:
        logger.warning(
            "[DB:state] FORCE_SCRAPE active — bypassing 24h gate for all %d URLs.",
            len(normalised_urls),
        )
        for url in normalised_urls:
            print(f"[SCRAPE CHECK] URL: {url}")
            print("[SCRAPE CHECK] Last scraped: N/A (force mode)")
            print("[SCRAPE CHECK] Decision: SCRAPE")
        return normalised_urls

    sql = """
        SELECT url, last_scraped_at
        FROM scrape_state
        WHERE url = ANY(%s)
    """
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql, (normalised_urls,))
                rows = {r["url"]: r["last_scraped_at"] for r in cur.fetchall()}
    except Exception as exc:
        # Fail-safe: if DB lookup fails, scrape everything rather than silently skip
        logger.error(
            "[DB:state] scrape_state lookup failed — defaulting to SCRAPE for all URLs: %s", exc
        )
        logger.error(traceback.format_exc())
        return normalised_urls

    now = datetime.utcnow()
    due: list[str] = []

    for url in normalised_urls:
        last = rows.get(url)  # None if never scraped or null in DB

        print(f"[SCRAPE CHECK] URL: {url}")
        print(f"[SCRAPE CHECK] Last scraped: {last if last is not None else 'NULL'}")

        if last is None:
            print("[SCRAPE CHECK] Decision: SCRAPE")
            logger.info("[DB:state] %-70s → SCRAPE  (never scraped)", url)
            due.append(url)
        else:
            # Ensure comparison is timezone-naive UTC on both sides
            if hasattr(last, "tzinfo") and last.tzinfo is not None:
                last = last.replace(tzinfo=None)  # strip tz if Neon returns tz-aware
            delta = now - last
            delta_hours = delta.total_seconds() / 3600

            if delta_hours >= interval_hours:
                print("[SCRAPE CHECK] Decision: SCRAPE")
                logger.info(
                    "[DB:state] %-70s → SCRAPE  (last=%.1fh ago)", url, delta_hours
                )
                due.append(url)
            else:
                hours_remaining = interval_hours - delta_hours
                print("[SCRAPE CHECK] Decision: SKIP")
                logger.info(
                    "[DB:state] %-70s → SKIP    (last=%.1fh ago, next in %.1fh)",
                    url, delta_hours, hours_remaining,
                )

    return due
