"""Common scraper logic for Bazos.sk website."""

import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
from datetime import datetime

from deal_watcher.scrapers.base_scraper import BaseScraper
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class BazosScraper(BaseScraper):
    """Common scraper for Bazos.sk website."""

    LISTINGS_PER_PAGE = 20

    def __init__(self, config: Dict[str, Any], http_client):
        """Initialize Bazos scraper."""
        super().__init__(config, http_client)
        self.base_url = self._extract_base_url(self.url)

    def _extract_base_url(self, url: str) -> str:
        """Extract base URL from full URL."""
        match = re.match(r'(https?://[^/]+)', url)
        return match.group(1) if match else url

    def get_page_url(self, page_number: int) -> str:
        """
        Get URL for a specific page number.

        Args:
            page_number: Page number (0-indexed)

        Returns:
            Full URL for the page
        """
        if page_number == 0:
            return self.url

        offset = page_number * self.LISTINGS_PER_PAGE
        # Remove trailing slash if present
        base_url = self.url.rstrip('/')
        return f"{base_url}/{offset}/"

    def extract_listing_id(self, url: str) -> Optional[str]:
        """
        Extract listing ID from Bazos URL.

        Args:
            url: Listing URL

        Returns:
            Listing ID or None
        """
        # Pattern: /inzerat/{ID}/
        match = re.search(r'/inzerat/(\d+)/', url)
        if match:
            return match.group(1)
        return None

    def scrape_list_page(self, page_number: int = 0) -> List[Dict[str, Any]]:
        """
        Scrape a list page from Bazos.

        Args:
            page_number: Page number (0-indexed)

        Returns:
            List of basic listing information
        """
        url = self.get_page_url(page_number)
        soup = self.fetch_page(url)

        if not soup:
            return []

        listings = []

        # Find all listing containers
        # Bazos uses <div class="inzeraty inzerat"> for each listing
        listing_divs = soup.find_all('div', class_='inzerat')

        for listing_div in listing_divs:
            try:
                listing_data = self._parse_list_item(listing_div)
                if listing_data:
                    listings.append(listing_data)
            except Exception as e:
                logger.warning(f"Error parsing listing: {e}")
                continue

        return listings

    def _parse_list_item(self, listing_div) -> Optional[Dict[str, Any]]:
        """
        Parse a single listing from list page.

        Args:
            listing_div: BeautifulSoup div element

        Returns:
            Dictionary with listing data or None
        """
        try:
            # Find title and URL
            title_link = listing_div.find('a', class_='nadpis')
            if not title_link:
                return None

            title = title_link.get_text(strip=True)
            relative_url = title_link.get('href', '')
            full_url = urljoin(self.base_url, relative_url)

            # Extract listing ID
            listing_id = self.extract_listing_id(full_url)
            if not listing_id:
                return None

            # Extract price
            price_text = listing_div.find('div', class_='inzeratycena')
            price = None
            if price_text:
                price = self._parse_price(price_text.get_text(strip=True))

            # Extract location
            location_div = listing_div.find('div', class_='inzeratylok')
            location = None
            postal_code = None
            if location_div:
                location_text = location_div.get_text(strip=True)
                location, postal_code = self._parse_location(location_text)

            # Extract view count
            view_count = None
            view_span = listing_div.find('span', string=re.compile(r'\d+\s*x'))
            if view_span:
                view_match = re.search(r'(\d+)\s*x', view_span.get_text())
                if view_match:
                    view_count = int(view_match.group(1))

            # Extract description
            description_div = listing_div.find('div', class_='popis')
            description = description_div.get_text(strip=True) if description_div else ''

            # Extract image URL
            image_url = None
            img_tag = listing_div.find('img')
            if img_tag and img_tag.get('src'):
                image_url = urljoin(self.base_url, img_tag.get('src'))

            return {
                'external_id': listing_id,
                'title': title,
                'url': full_url,
                'price': price,
                'location': location,
                'postal_code': postal_code,
                'view_count': view_count,
                'description': description,
                'image_url': image_url
            }

        except Exception as e:
            logger.error(f"Error parsing list item: {e}")
            return None

    def _parse_price(self, price_text: str) -> Optional[float]:
        """
        Parse price from text.

        Args:
            price_text: Price text (e.g., "12 500 €", "Dohodou")

        Returns:
            Price as float or None
        """
        # Handle special cases
        if not price_text or price_text.lower() in ['dohodou', 'v texte']:
            return None

        # Remove spaces, non-numeric characters except digits and decimal point
        cleaned = re.sub(r'[^\d,.]', '', price_text)
        # Replace comma with dot
        cleaned = cleaned.replace(',', '.')

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _parse_location(self, location_text: str) -> tuple:
        """
        Parse location and postal code.

        Args:
            location_text: Location text (e.g., "Bratislava 821 01")

        Returns:
            Tuple of (location, postal_code)
        """
        # Try to extract postal code (usually 3-5 digits, optionally with space)
        postal_match = re.search(r'(\d{3}\s?\d{2})$', location_text)

        if postal_match:
            postal_code = postal_match.group(1).strip()
            location = location_text[:postal_match.start()].strip()
            return location, postal_code

        return location_text.strip(), None

    def scrape_detail_page(self, listing_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detail page for a listing.

        Args:
            listing_url: Full URL to listing detail page

        Returns:
            Dictionary with detailed information or None
        """
        soup = self.fetch_page(listing_url)

        if not soup:
            return None

        try:
            # Extract full description
            description_div = soup.find('div', class_='popisdetail')
            description = description_div.get_text(strip=True) if description_div else ''

            # Extract all images
            images = []
            img_divs = soup.find_all('div', class_='carousel-item')
            for img_div in img_divs:
                img_tag = img_div.find('img')
                if img_tag and img_tag.get('src'):
                    img_url = urljoin(self.base_url, img_tag.get('src'))
                    images.append(img_url)

            # Extract metadata (posted date, contact info, etc.)
            metadata = {}

            # Try to find date posted
            date_pattern = re.compile(r'\[(\d{2}\.\d{2}\.\s*\d{4})\]')
            date_match = soup.find(string=date_pattern)
            if date_match:
                date_str = date_pattern.search(str(date_match)).group(1)
                try:
                    metadata['posted_date'] = datetime.strptime(date_str.strip(), '%d.%m. %Y').isoformat()
                except ValueError:
                    pass

            return {
                'description': description,
                'images': images,
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Error scraping detail page {listing_url}: {e}")
            return None
