"""Test script to verify scraping functionality without database."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deal_watcher.utils.http_client import HTTPClient
from deal_watcher.utils.logger import setup_logger
from deal_watcher.scrapers.auto_scraper import AutoScraper
from deal_watcher.scrapers.reality_scraper import RealityScraper
from deal_watcher.filters.auto_filter import AutoFilter
from deal_watcher.filters.reality_filter import RealityFilter

logger = setup_logger('test', level='INFO')

def test_bmw_scraper():
    """Test BMW scraper."""
    logger.info("=" * 60)
    logger.info("Testing BMW Scraper")
    logger.info("=" * 60)

    config = {
        'name': 'BMW Test',
        'url': 'https://auto.bazos.sk/bmw/',
        'type': 'auto',
        'max_pages': 2,
        'filters': {
            'keywords_any': ['E36', 'E46', 'E39'],
            'keywords_all': ['benzin', 'manuál'],
            'keywords_engine': ['6 valec', '6-valec', '6 cylinder'],
            'keywords_excluded': ['havarovan', 'automat']
        }
    }

    http_client = HTTPClient(timeout=30, request_delay=2.0)
    scraper = AutoScraper(config, http_client)
    filter_obj = AutoFilter(config['filters'])

    # Scrape listings
    listings = scraper.run()
    logger.info(f"\nScraped {len(listings)} total listings")

    if listings:
        logger.info("\nFirst 3 listings:")
        for i, listing in enumerate(listings[:3]):
            logger.info(f"\nListing {i+1}:")
            logger.info(f"  ID: {listing.get('external_id')}")
            logger.info(f"  Title: {listing.get('title')[:60]}")
            logger.info(f"  Price: {listing.get('price')} EUR")
            logger.info(f"  Location: {listing.get('location')}")
            logger.info(f"  URL: {listing.get('url')[:70]}")

        # Test filtering
        logger.info(f"\nApplying filters...")
        matches = [l for l in listings if filter_obj.matches(l, detailed=False)]
        logger.info(f"Found {len(matches)} matches after filtering")

        if matches:
            logger.info("\nMatching listings:")
            for listing in matches[:5]:
                logger.info(f"  - {listing.get('title')[:60]} - {listing.get('price')} EUR")

    http_client.close()
    return len(listings) > 0

def test_reality_scraper():
    """Test Reality scraper."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Reality Scraper")
    logger.info("=" * 60)

    config = {
        'name': 'Land Test',
        'url': 'https://reality.bazos.sk/predam/pozemok/',
        'type': 'reality',
        'max_pages': 2,
        'filters': {
            'price_max': 400000,
            'area_min': 40000,
            'keywords_excluded': ['stavebný pozemok']
        }
    }

    http_client = HTTPClient(timeout=30, request_delay=2.0)
    scraper = RealityScraper(config, http_client)
    filter_obj = RealityFilter(config['filters'])

    # Scrape listings
    listings = scraper.run()
    logger.info(f"\nScraped {len(listings)} total listings")

    if listings:
        logger.info("\nFirst 3 listings:")
        for i, listing in enumerate(listings[:3]):
            logger.info(f"\nListing {i+1}:")
            logger.info(f"  ID: {listing.get('external_id')}")
            logger.info(f"  Title: {listing.get('title')[:60]}")
            logger.info(f"  Price: {listing.get('price')} EUR")
            logger.info(f"  Location: {listing.get('location')}")

        # Test filtering
        logger.info(f"\nApplying filters...")
        matches = [l for l in listings if filter_obj.matches(l, detailed=False)]
        logger.info(f"Found {len(matches)} matches after filtering")

        if matches:
            logger.info("\nMatching listings (with large land area):")
            for listing in matches[:5]:
                logger.info(f"  - {listing.get('title')[:60]} - {listing.get('price')} EUR")

    http_client.close()
    return len(listings) > 0

if __name__ == '__main__':
    logger.info("Testing Deal Watcher Scrapers\n")

    bmw_ok = test_bmw_scraper()
    reality_ok = test_reality_scraper()

    logger.info("\n" + "=" * 60)
    logger.info("Test Results:")
    logger.info(f"  BMW Scraper: {'✓ PASS' if bmw_ok else '✗ FAIL'}")
    logger.info(f"  Reality Scraper: {'✓ PASS' if reality_ok else '✗ FAIL'}")
    logger.info("=" * 60)

    sys.exit(0 if (bmw_ok and reality_ok) else 1)
