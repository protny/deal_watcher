"""Base scraper abstract class."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
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

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a page.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object or None if fetch failed
        """
        try:
            response = self.http_client.get(url)
            if response and response.status_code == 200:
                return BeautifulSoup(response.content, 'lxml')
            else:
                logger.warning(f"Failed to fetch {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def run(self) -> List[Dict[str, Any]]:
        """
        Run the scraper for configured number of pages.

        Returns:
            List of all scraped listings
        """
        all_listings = []

        logger.info(f"Starting scraper: {self.name}")

        for page_num in range(self.max_pages):
            logger.info(f"Scraping page {page_num + 1}/{self.max_pages}")

            try:
                listings = self.scrape_list_page(page_num)

                if not listings:
                    logger.info(f"No listings found on page {page_num + 1}, stopping")
                    break

                logger.info(f"Found {len(listings)} listings on page {page_num + 1}")
                all_listings.extend(listings)

            except Exception as e:
                logger.error(f"Error scraping page {page_num + 1}: {e}")
                continue

        logger.info(f"Scraper {self.name} completed: {len(all_listings)} total listings")
        return all_listings
