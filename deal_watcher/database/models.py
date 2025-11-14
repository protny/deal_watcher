"""SQLAlchemy models for the deal_watcher database."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DECIMAL, Boolean,
    TIMESTAMP, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Category(Base):
    """Category model representing different scraping categories."""

    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'auto', 'reality'
    url = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    deals = relationship("Deal", back_populates="category")
    scraping_runs = relationship("ScrapingRun", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', type='{self.type}')>"


class Deal(Base):
    """Deal model representing a scraped listing."""

    __tablename__ = 'deals'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'))
    title = Column(Text, nullable=False)
    description = Column(Text)
    current_price = Column(DECIMAL(12, 2))
    location = Column(String(200))
    postal_code = Column(String(10))
    url = Column(String(500), nullable=False)
    first_seen_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_seen_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_checked_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    view_count = Column(Integer)
    deal_metadata = Column(JSONB)  # Flexible storage for category-specific data
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="deals")
    price_history = relationship("PriceHistory", back_populates="deal", cascade="all, delete-orphan")
    images = relationship("DealImage", back_populates="deal", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_deals_external_id', 'external_id'),
        Index('idx_deals_category', 'category_id'),
        Index('idx_deals_active', 'is_active'),
        Index('idx_deals_metadata', 'deal_metadata', postgresql_using='gin'),
        Index('idx_deals_first_seen', 'first_seen_at'),
    )

    def __repr__(self):
        return f"<Deal(id={self.id}, external_id='{self.external_id}', title='{self.title[:50]}')>"


class PriceHistory(Base):
    """Price history model tracking price changes over time."""

    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    price = Column(DECIMAL(12, 2), nullable=False)
    changed_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="price_history")

    # Indexes and constraints
    __table_args__ = (
        Index('idx_price_history_deal', 'deal_id'),
        UniqueConstraint('deal_id', 'price', 'changed_at', name='idx_price_history_unique'),
    )

    def __repr__(self):
        return f"<PriceHistory(id={self.id}, deal_id={self.deal_id}, price={self.price})>"


class DealImage(Base):
    """Deal image model storing image URLs."""

    __tablename__ = 'deal_images'

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey('deals.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    deal = relationship("Deal", back_populates="images")

    # Indexes
    __table_args__ = (
        Index('idx_deal_images_deal', 'deal_id'),
    )

    def __repr__(self):
        return f"<DealImage(id={self.id}, deal_id={self.deal_id}, is_primary={self.is_primary})>"


class ScrapingRun(Base):
    """Scraping run model tracking scraper execution history."""

    __tablename__ = 'scraping_runs'

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'))
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)
    status = Column(String(50), default='running')  # 'running', 'completed', 'failed'
    listings_processed = Column(Integer, default=0)
    new_deals_found = Column(Integer, default=0)
    price_changes_detected = Column(Integer, default=0)
    deals_disappeared = Column(Integer, default=0)
    error_message = Column(Text)

    # Relationships
    category = relationship("Category", back_populates="scraping_runs")

    # Indexes
    __table_args__ = (
        Index('idx_scraping_runs_status', 'status'),
        Index('idx_scraping_runs_started', 'started_at'),
    )

    def __repr__(self):
        return f"<ScrapingRun(id={self.id}, category_id={self.category_id}, status='{self.status}')>"
