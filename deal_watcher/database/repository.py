"""Database repository for deal_watcher."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from deal_watcher.database.models import Base, Category, Deal, PriceHistory, DealImage, ScrapingRun
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class DealRepository:
    """Repository for database operations."""

    def __init__(self, connection_string: str):
        """
        Initialize repository.

        Args:
            connection_string: PostgreSQL connection string
        """
        self.engine = create_engine(connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("Database repository initialized")

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        session = self.get_session()
        try:
            return session.query(Category).filter(Category.id == category_id).first()
        finally:
            session.close()

    def get_deal_by_external_id(self, external_id: str) -> Optional[Deal]:
        """Get deal by external ID."""
        session = self.get_session()
        try:
            return session.query(Deal).filter(Deal.external_id == external_id).first()
        finally:
            session.close()

    def create_or_update_deal(
        self,
        listing_data: Dict[str, Any],
        category_id: int
    ) -> tuple[Deal, bool, bool]:
        """
        Create new deal or update existing one.

        Args:
            listing_data: Dictionary with listing data
            category_id: Category ID

        Returns:
            Tuple of (deal, is_new, price_changed)
        """
        session = self.get_session()
        is_new = False
        price_changed = False

        try:
            external_id = listing_data.get('external_id')
            deal = session.query(Deal).filter(Deal.external_id == external_id).first()

            if deal:
                # Update existing deal
                old_price = deal.current_price
                new_price = listing_data.get('price')

                # Update fields
                deal.title = listing_data.get('title', deal.title)
                deal.description = listing_data.get('description', deal.description)
                deal.location = listing_data.get('location', deal.location)
                deal.postal_code = listing_data.get('postal_code', deal.postal_code)
                deal.view_count = listing_data.get('view_count', deal.view_count)
                deal.last_seen_at = datetime.utcnow()
                deal.last_checked_at = datetime.utcnow()
                deal.updated_at = datetime.utcnow()
                deal.is_active = True

                # Check for price change
                if new_price is not None and old_price != new_price:
                    deal.current_price = Decimal(str(new_price))
                    price_changed = True

                    # Add price history entry
                    price_history = PriceHistory(
                        deal_id=deal.id,
                        price=Decimal(str(new_price)),
                        changed_at=datetime.utcnow()
                    )
                    session.add(price_history)
                    logger.info(f"Price changed for {external_id}: {old_price} -> {new_price}")

            else:
                # Create new deal
                is_new = True
                price = listing_data.get('price')

                deal = Deal(
                    external_id=external_id,
                    category_id=category_id,
                    title=listing_data.get('title'),
                    description=listing_data.get('description'),
                    current_price=Decimal(str(price)) if price is not None else None,
                    location=listing_data.get('location'),
                    postal_code=listing_data.get('postal_code'),
                    url=listing_data.get('url'),
                    view_count=listing_data.get('view_count'),
                    extra_data=listing_data.get('extra_data', {}),
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                    last_checked_at=datetime.utcnow(),
                    is_active=True
                )
                session.add(deal)
                session.flush()  # Get deal.id

                # Add initial price to history
                if price is not None:
                    price_history = PriceHistory(
                        deal_id=deal.id,
                        price=Decimal(str(price)),
                        changed_at=datetime.utcnow()
                    )
                    session.add(price_history)

                # Add image if present
                image_url = listing_data.get('image_url')
                if image_url:
                    image = DealImage(
                        deal_id=deal.id,
                        image_url=image_url,
                        is_primary=True
                    )
                    session.add(image)

                logger.info(f"Created new deal: {external_id}")

            session.commit()
            session.refresh(deal)
            return deal, is_new, price_changed

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating/updating deal: {e}")
            raise
        finally:
            session.close()

    def mark_deals_as_inactive(self, external_ids: List[str]):
        """Mark deals as inactive (disappeared from listings)."""
        session = self.get_session()
        try:
            count = session.query(Deal).filter(
                Deal.external_id.in_(external_ids)
            ).update({
                'is_active': False,
                'updated_at': datetime.utcnow()
            }, synchronize_session=False)

            session.commit()
            logger.info(f"Marked {count} deals as inactive")
            return count

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error marking deals as inactive: {e}")
            raise
        finally:
            session.close()

    def create_scraping_run(self, category_id: int) -> ScrapingRun:
        """Create a new scraping run record."""
        session = self.get_session()
        try:
            run = ScrapingRun(
                category_id=category_id,
                started_at=datetime.utcnow(),
                status='running'
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            logger.info(f"Created scraping run {run.id} for category {category_id}")
            return run
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating scraping run: {e}")
            raise
        finally:
            session.close()

    def update_scraping_run(
        self,
        run_id: int,
        status: str,
        listings_processed: int = 0,
        new_deals_found: int = 0,
        price_changes_detected: int = 0,
        deals_disappeared: int = 0,
        error_message: Optional[str] = None
    ):
        """Update scraping run with results."""
        session = self.get_session()
        try:
            run = session.query(ScrapingRun).filter(ScrapingRun.id == run_id).first()
            if run:
                run.status = status
                run.completed_at = datetime.utcnow()
                run.listings_processed = listings_processed
                run.new_deals_found = new_deals_found
                run.price_changes_detected = price_changes_detected
                run.deals_disappeared = deals_disappeared
                run.error_message = error_message
                session.commit()
                logger.info(f"Updated scraping run {run_id}: {status}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error updating scraping run: {e}")
            raise
        finally:
            session.close()

    def get_active_deals_by_category(self, category_id: int) -> List[str]:
        """Get list of external IDs for active deals in a category."""
        session = self.get_session()
        try:
            deals = session.query(Deal.external_id).filter(
                Deal.category_id == category_id,
                Deal.is_active == True
            ).all()
            return [deal[0] for deal in deals]
        finally:
            session.close()
