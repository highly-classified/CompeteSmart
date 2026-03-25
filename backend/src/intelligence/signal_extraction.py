from sqlalchemy.orm import Session
from src.models import ExtractedContent, Snapshot, Signal
import logging

logger = logging.getLogger(__name__)

class SignalExtractor:
    def __init__(self, db: Session):
        self.db = db

    def extract_signals(self) -> int:
        """
        Pulls raw data from `extracted_content` and converts it into `signals`.
        Ensures each signal is a cleaned, categorized, and deduplicated semantic unit.
        """
        logger.info("[SignalExtraction] Starting signal extraction from extracted_content...")

        # Find content that hasn't been converted to signals yet
        # Join with Snapshot to get competitor_id
        unprocessed = self.db.query(ExtractedContent, Snapshot.competitor_id).join(
            Snapshot, ExtractedContent.snapshot_id == Snapshot.id
        ).outerjoin(
            Signal,
            (ExtractedContent.snapshot_id == Signal.snapshot_id) &
            (ExtractedContent.content == Signal.content)
        ).filter(Signal.id == None).all()

        if not unprocessed:
            logger.info("[SignalExtraction] No new extracted content to process.")
            return 0

        count = 0
        for ext_content, comp_id in unprocessed:
            # 1. Clean
            content = ext_content.content.strip() if ext_content.content else ""
            if not content:
                continue

            # 2. Categorize (based on content_type from scraper)
            category = ext_content.content_type or "general"

            # 3. Create Signal
            new_signal = Signal(
                competitor_id=comp_id,
                snapshot_id=ext_content.snapshot_id,
                content=content,
                category=category
            )
            self.db.add(new_signal)
            count += 1

        self.db.commit()
        logger.info(f"[SignalExtraction] Successfully extracted {count} signals.")
        return count
