"""
seed_history.py
---------------
Generates realistic, non-uniform synthetic historical data (2022–2023)
to demonstrate messaging evolution for Urban Company services.

Messaging Strategy:
* 2022: Focus on Price & Speed ("Affordable", "Book in 1 min", "Low cost").
* 2023: Focus on Trust & Professionals ("Verified", "Experts", "Top-rated").
* 2024: (Live Data) Focus on Premium/AI ("AI-powered", "Luxe", "Smart").
"""

from __future__ import annotations

import logging
import random
from datetime import datetime

import db
from config import COMPETITORS
from utils import compute_hash, normalize_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# THEMATIC DATA POOLS
# Keywords used to customize phrases based on URL content
SERVICE_HINTS = {
    "bathroom": "bathroom and toilet cleaning",
    "cleaning": "professional home cleaning",
    "services": "expert home maintenance",
    "chennai": "urban services across Chennai",
}

THEMES = {
    2022: [
        "Affordable {service} starting at just ₹499",
        "Quick {service} booking in less than 60 seconds",
        "Get your {service} done today with our fast turnaround",
        "Budget-friendly {service} for your daily needs",
        "Simplifying {service} for everyone at the lowest prices",
        "Book {service} now and save up to 20% on your first order",
        "Reliable and fast {service} available near you",
        "Value-for-money {service} with no hidden charges",
    ],
    2023: [
        "Verified professionals for all your {service} needs",
        "Experience top-rated {service} from background-checked experts",
        "Safety-first {service} with 100% satisfaction guarantee",
        "Expert technicians providing the best {service} in class",
        "Trusted by millions for quality {service} and reliability",
        "Our {service} professionals follow strict quality protocols",
        "Hassle-free {service} delivered by trained specialists",
        "Premium quality {service} you can always rely on",
    ],
}

def get_service_keyword(url: str) -> str:
    """Determine the most specific service keyword from the URL."""
    url = url.lower()
    for hint, keyword in SERVICE_HINTS.items():
        if hint in url:
            return keyword
    return "home services"

def generate_variations(year: int, service: str, count: int) -> list[str]:
    """Generate *count* semi-unique phrases for a specific year and service."""
    templates = THEMES[year]
    # Shuffle and pick to avoid identical lists
    sampled = random.sample(templates, min(count, len(templates)))
    
    # Apply minor wording variations
    results = []
    adjectives = ["", "Great", "Excellent", "Quality", "Professional"]
    
    for t in sampled:
        phrase = t.format(service=service)
        prefix = random.choice(adjectives)
        if prefix and not phrase.startswith(prefix):
            phrase = f"{prefix} {phrase.lower()}"
        results.append(phrase)
    
    return results

def seed():
    """Main seeder logic."""
    logger.info("[SEED] Starting synthetic history generation …")
    
    # Ensure DB is ready
    db.init_db()
    
    # Find Urban Company in config
    uc = next((c for c in COMPETITORS if c["name"] == "Urban Company"), None)
    if not uc:
        logger.error("[SEED] Urban Company not found in COMPETITORS config.")
        return

    comp_id = db.upsert_competitor(uc["name"], uc["domain"])
    
    urls = uc["urls"]
    years = [2022, 2023]
    # Snapshots per year: Feb, Jun, Oct
    months = [2, 6, 10]
    
    total_snapshots = 0
    total_chunks = 0
    
    for url in urls:
        norm_url = normalize_url(url)
        service_kw = get_service_keyword(norm_url)
        
        for year in years:
            for month in months:
                # Distribution across month
                day = random.randint(1, 28)
                ts = datetime(year, month, day, 10, 0, 0)
                
                # Create snapshot
                snapshot_id = db.create_snapshot(
                    comp_id, norm_url, is_synthetic=True, created_at=ts
                )
                total_snapshots += 1
                
                # Generate varied phrases
                phrases = generate_variations(year, service_kw, count=4)
                
                # Insert chunks
                for phrase in phrases:
                    content_hash = compute_hash(f"{norm_url}-{ts.isoformat()}-{phrase}")
                    # Label contextually
                    ctype = "service" if "service" in phrase.lower() else "paragraph"
                    
                    inserted = db.insert_content_chunk(
                        snapshot_id=snapshot_id,
                        content_type=ctype,
                        content=phrase,
                        content_hash=content_hash,
                        is_synthetic=True,
                        created_at=ts
                    )
                    if inserted:
                        total_chunks += 1
                
                # Print debug for first snapshot of the year
                if month == 2:
                    print(f"[SEED] Year: {year} | URL: {norm_url} | Chunks: {len(phrases)}")
                    print(f"[SEED] Sample: {phrases[0]}")

    logger.info(
        "[SEED] Complete ✓ Seeded %d snapshots and %d chunks across 2022-2023.",
        total_snapshots, total_chunks
    )

if __name__ == "__main__":
    seed()
