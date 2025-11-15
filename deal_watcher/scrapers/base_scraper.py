"""Base scraper abstract class."""

import os
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from deal_watcher.utils.http_client import HTTPClient
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, config: Dict[str, Any], http_client: HTTPClient):
        """
        Initialize base scraper.

        Args:
            config: Scraper configuration dictionary
            http_client: HTTP client instance
        """
        self.config = config
        self.http_client = http_client
        self.name = config.get('name', 'Unknown')
        self.url = config.get('url')
        self.max_pages = config.get('max_pages', 10)
        self.filters = config.get('filters', {})
        self.mode = config.get('mode', 'full')  # 'full' or 'new'
        self.days_back = config.get('days_back', 7)
        self.cache_pages = config.get('cache_pages', False)
        self.cache_dir = '.cache/pages'

        # Create cache directory if needed
        if self.cache_pages and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    @abstractmethod
    def scrape_list_page(self, page_number: int = 0) -> List[Dict[str, Any]]:
        """
        Scrape a list page and extract basic listing information.

        Args:
            page_number: Page number to scrape (0-indexed)

        Returns:
            List of dictionaries containing basic listing info
        """
        pass

    @abstractmethod
    def scrape_detail_page(self, listing_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a detail page for a specific listing.

        Args:
            listing_url: URL of the listing detail page

        Returns:
            Dictionary with detailed listing information or None if failed
        """
        pass

    @abstractmethod
    def extract_listing_id(self, url: str) -> Optional[str]:
        """
        Extract unique listing ID from URL.

        Args:
            url: Listing URL

        Returns:
            Listing ID or None if extraction failed
        """
        pass

    def fetch_page(self, url: str, cache_key: Optional[str] = None) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a page, with optional caching.

        Args:
            url: URL to fetch
            cache_key: Optional cache key (if not provided, uses URL hash)

        Returns:
            BeautifulSoup object or None if fetch failed
        """
        # Generate cache filename
        if cache_key is None:
            cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.html")

        # Try to load from cache if enabled
        if self.cache_pages and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    logger.debug(f"Loading from cache: {cache_file}")
                    return BeautifulSoup(f.read(), 'lxml')
            except Exception as e:
                logger.warning(f"Error loading cache {cache_file}: {e}")

        # Fetch from web
        try:
            response = self.http_client.get(url)
            if response and response.status_code == 200:
                content = response.content

                # Save to cache if enabled
                if self.cache_pages:
                    try:
                        with open(cache_file, 'wb') as f:
                            f.write(content)
                        logger.debug(f"Saved to cache: {cache_file}")
                    except Exception as e:
                        logger.warning(f"Error saving cache: {e}")

                return BeautifulSoup(content, 'lxml')
            else:
                logger.warning(f"Failed to fetch {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def run(self) -> List[Dict[str, Any]]:
        """
        Run the scraper for configured number of pages.

        In 'new' mode, stops when encountering listings older than days_back.
        In 'full' mode, scrapes all max_pages.

        Returns:
            List of all scraped listings
        """
        all_listings = []
        cutoff_date = None

        logger.info(f"Starting scraper: {self.name} (mode: {self.mode})")

        if self.mode == 'new':
            cutoff_date = datetime.now() - timedelta(days=self.days_back)
            logger.info(f"Only processing listings from last {self.days_back} days (since {cutoff_date.strftime('%Y-%m-%d')})")

        for page_num in range(self.max_pages):
            logger.info(f"Scraping page {page_num + 1}/{self.max_pages}")

            try:
                listings = self.scrape_list_page(page_num)

                if not listings:
                    logger.info(f"No listings found on page {page_num + 1}, stopping")
                    break

                logger.info(f"Found {len(listings)} listings on page {page_num + 1}")

                # In 'new' mode, filter by date and stop if all listings are too old
                if self.mode == 'new' and cutoff_date:
                    recent_listings = []
                    all_too_old = True

                    for listing in listings:
                        posted_date = listing.get('posted_date')
                        if posted_date and isinstance(posted_date, datetime):
                            if posted_date >= cutoff_date:
                                recent_listings.append(listing)
                                all_too_old = False
                            else:
                                logger.debug(f"Listing {listing.get('external_id')} too old: {posted_date.strftime('%Y-%m-%d')}")
                        else:
                            # If no date, include it (don't want to miss anything)
                            recent_listings.append(listing)
                            all_too_old = False

                    all_listings.extend(recent_listings)
                    logger.info(f"  {len(recent_listings)}/{len(listings)} listings are recent enough")

                    # Stop if all listings on this page are too old
                    if all_too_old:
                        logger.info(f"All listings on page {page_num + 1} are older than {self.days_back} days, stopping")
                        break
                else:
                    # Full mode - add all listings
                    all_listings.extend(listings)

            except Exception as e:
                logger.error(f"Error scraping page {page_num + 1}: {e}")
                continue

        logger.info(f"Scraper {self.name} completed: {len(all_listings)} total listings")
        return all_listings
