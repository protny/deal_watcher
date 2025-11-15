"""
Processor script - reads cached HTML pages, extracts listings, applies filters, saves to DB.

This script processes previously downloaded HTML pages from the cache directory.
It extracts listings, applies configured filters, and saves matches to the database.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from deal_watcher.utils.logger import setup_logger, get_logger
from deal_watcher.database.repository import DealRepository
from deal_watcher.scrapers.bazos_scraper import BazosScraper
from deal_watcher.scrapers.auto_scraper import AutoScraper
from deal_watcher.scrapers.reality_scraper import RealityScraper
from deal_watcher.filters.auto_filter import AutoFilter
from deal_watcher.filters.reality_filter import RealityFilter
from deal_watcher.utils.http_client import HTTPClient

# Load environment variables
load_dotenv()

logger = None


def load_config(config_path: str = 'deal_watcher/config/config.json') -> Dict[str, Any]:
    """
    Load processing configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Replace environment variables in connection string
        db_config = config.get('database', {})
        conn_string = db_config.get('connection_string', '')
        if '${DB_CONNECTION_STRING}' in conn_string:
            conn_string = os.getenv('DB_CONNECTION_STRING', '')
            if not conn_string:
                raise ValueError("DB_CONNECTION_STRING environment variable not set")
            config['database']['connection_string'] = conn_string

        return config

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)


def get_cache_directory_for_scraper(scraper_config: Dict[str, Any]) -> Path:
    """
    Get cache directory for a scraper based on its configuration.

    Args:
        scraper_config: Scraper configuration

    Returns:
        Path to cache directory
    """
    # Map scraper to cache subdirectory
    # This maps the scraper configs to download_config.json cache_subdir values
    url = scraper_config.get('url', '')

    if 'auto.bazos.sk/bmw' in url:
        return Path('cache/bazos/auto-bmw')
    elif 'reality.bazos.sk/predam/pozemok' in url:
        return Path('cache/bazos/reality-pozemok')
    elif 'reality.bazos.sk/predam/dom' in url:
        return Path('cache/bazos/reality-dom')
    elif 'reality.bazos.sk/predam/chata' in url:
        return Path('cache/bazos/reality-chata')
    else:
        logger.warning(f"Unknown URL pattern: {url}")
        return None


def read_cached_pages(cache_dir: Path) -> List[BeautifulSoup]:
    """
    Read all cached HTML pages from a directory.

    Args:
        cache_dir: Directory containing cached HTML files

    Returns:
        List of BeautifulSoup objects
    """
    if not cache_dir.exists():
        logger.warning(f"Cache directory does not exist: {cache_dir}")
        return []

    pages = []
    html_files = sorted(cache_dir.glob('page_*.html'))

    logger.info(f"Found {len(html_files)} cached pages in {cache_dir}")

    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'lxml')
                pages.append(soup)
        except Exception as e:
            logger.error(f"Error reading {html_file}: {e}")

    return pages


def extract_listings_from_pages(
    pages: List[BeautifulSoup],
    scraper: BazosScraper
) -> List[Dict[str, Any]]:
    """
    Extract all listings from cached pages using scraper's parsing logic.

    Args:
        pages: List of BeautifulSoup objects
        scraper: Scraper instance to use for parsing

    Returns:
        List of listing dictionaries
    """
    all_listings = []

    for page_num, soup in enumerate(pages):
        try:
            # Find all listing containers
            listing_divs = soup.find_all('div', class_='inzeraty')
            logger.debug(f"Page {page_num + 1}: found {len(listing_divs)} listings")

            for listing_div in listing_divs:
                try:
                    listing_data = scraper._parse_list_item(listing_div)
                    if listing_data:
                        all_listings.append(listing_data)
                except Exception as e:
                    logger.warning(f"Error parsing listing: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error processing page {page_num + 1}: {e}")

    logger.info(f"Extracted {len(all_listings)} total listings from cached pages")
    return all_listings


def get_scraper(scraper_config: Dict[str, Any], http_client: HTTPClient):
    """
    Factory function to create appropriate scraper.

    Args:
        scraper_config: Scraper configuration
        http_client: HTTP client instance (for fetching detail pages)

    Returns:
        Scraper instance
    """
    scraper_type = scraper_config.get('type')

    if scraper_type == 'auto':
        return AutoScraper(scraper_config, http_client)
    elif scraper_type == 'reality':
        return RealityScraper(scraper_config, http_client)
    else:
        raise ValueError(f"Unknown scraper type: {scraper_type}")


def get_filter(scraper_config: Dict[str, Any]):
    """
    Factory function to create appropriate filter.

    Args:
        scraper_config: Scraper configuration

    Returns:
        Filter instance
    """
    scraper_type = scraper_config.get('type')
    filter_config = scraper_config.get('filters', {})

    if scraper_type == 'auto':
        return AutoFilter(filter_config)
    elif scraper_type == 'reality':
        return RealityFilter(filter_config)
    else:
        raise ValueError(f"Unknown filter type: {scraper_type}")


def process_scraper_from_cache(
    scraper_config: Dict[str, Any],
    http_client: HTTPClient,
    repository: DealRepository
) -> Dict[str, int]:
    """
    Process a scraper by reading from cached HTML files.

    Args:
        scraper_config: Scraper configuration
        http_client: HTTP client (for detail page fetches)
        repository: Database repository

    Returns:
        Statistics dictionary
    """
    name = scraper_config.get('name', 'Unknown')
    category_id = scraper_config.get('category_id')

    logger.info(f"=" * 60)
    logger.info(f"Processing: {name}")
    logger.info(f"=" * 60)

    # Get cache directory
    cache_dir = get_cache_directory_for_scraper(scraper_config)
    if not cache_dir or not cache_dir.exists():
        logger.error(f"Cache directory not found for {name}")
        return {
            'listings_processed': 0,
            'matches_found': 0,
            'new_deals_found': 0,
            'price_changes_detected': 0
        }

    # Create scraping run
    run = repository.create_scraping_run(category_id)

    stats = {
        'listings_processed': 0,
        'matches_found': 0,
        'new_deals_found': 0,
        'price_changes_detected': 0
    }

    try:
        # Read cached HTML pages
        pages = read_cached_pages(cache_dir)
        if not pages:
            logger.warning(f"No cached pages found for {name}")
            return stats

        # Create scraper and filter
        scraper = get_scraper(scraper_config, http_client)
        listing_filter = get_filter(scraper_config)

        # Extract listings from cached pages
        listings = extract_listings_from_pages(pages, scraper)
        stats['listings_processed'] = len(listings)

        logger.info(f"Processing {len(listings)} listings...")

        # Process each listing
        for listing in listings:
            try:
                external_id = listing.get('external_id')
                detail_url = listing.get('url')

                # Fetch detailed data (still need to fetch detail pages live)
                logger.debug(f"Fetching details for listing {external_id}")
                detail_data = scraper.scrape_detail_page(detail_url)

                if detail_data:
                    # Merge detail data into listing
                    listing.update(detail_data)

                    # Apply filter on detailed data
                    if listing_filter.matches(listing, detailed=True):
                        # Listing matches! Save to database
                        stats['matches_found'] += 1
                        deal, is_new, price_changed = repository.create_or_update_deal(
                            listing,
                            category_id
                        )

                        if is_new:
                            stats['new_deals_found'] += 1
                            logger.info(f"✓ NEW: {listing.get('title')} - {listing.get('price')}€ (ID: {external_id})")
                        elif price_changed:
                            stats['price_changes_detected'] += 1
                            logger.info(f"↓ PRICE CHANGE: {listing.get('title')} - {listing.get('price')}€ (ID: {external_id})")

            except Exception as e:
                logger.error(f"Error processing listing: {e}")
                continue

        # Update scraping run
        repository.update_scraping_run(
            run.id,
            status='completed',
            listings_processed=stats['listings_processed'],
            new_deals_found=stats['new_deals_found'],
            price_changes_detected=stats['price_changes_detected']
        )

        logger.info(f"\n{name} completed:")
        logger.info(f"  - Listings processed: {stats['listings_processed']}")
        logger.info(f"  - Matches found: {stats['matches_found']}")
        logger.info(f"  - New deals: {stats['new_deals_found']}")
        logger.info(f"  - Price changes: {stats['price_changes_detected']}")

        return stats

    except Exception as e:
        error_msg = f"Error processing {name}: {e}"
        logger.error(error_msg)
        repository.update_scraping_run(
            run.id,
            status='failed',
            error_message=str(e)
        )
        return stats


def main():
    """Main entry point for processor."""
    global logger

    # Setup logger
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logger = setup_logger('processor', level=log_level)

    logger.info("=" * 60)
    logger.info("Deal Watcher - Processor")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Initialize HTTP client (for detail page fetches)
    scraping_config = config.get('scraping', {})
    http_client = HTTPClient(
        timeout=scraping_config.get('timeout_seconds', 30),
        max_retries=scraping_config.get('max_retries', 3),
        backoff_factor=scraping_config.get('retry_backoff_factor', 2.0),
        request_delay=scraping_config.get('request_delay_seconds', 2.5),
        user_agents=scraping_config.get('user_agents', [])
    )

    # Initialize database repository
    db_connection = config['database']['connection_string']
    repository = DealRepository(db_connection)

    # Ensure tables exist
    try:
        repository.create_tables()
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        sys.exit(1)

    # Process each enabled scraper
    total_stats = {
        'listings_processed': 0,
        'matches_found': 0,
        'new_deals_found': 0,
        'price_changes_detected': 0
    }

    scrapers = config.get('scrapers', [])
    enabled_scrapers = [s for s in scrapers if s.get('enabled', True)]

    logger.info(f"Found {len(enabled_scrapers)} enabled scrapers\n")

    for scraper_config in enabled_scrapers:
        stats = process_scraper_from_cache(scraper_config, http_client, repository)

        # Accumulate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    # Clean up
    http_client.close()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Processing Complete")
    logger.info("=" * 60)
    logger.info(f"Total listings processed: {total_stats['listings_processed']}")
    logger.info(f"Total matches found: {total_stats['matches_found']}")
    logger.info(f"Total new deals: {total_stats['new_deals_found']}")
    logger.info(f"Total price changes: {total_stats['price_changes_detected']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
