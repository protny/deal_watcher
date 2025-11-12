"""Main CLI application for deal_watcher."""

import os
import json
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv

from deal_watcher.utils.logger import setup_logger, get_logger
from deal_watcher.utils.http_client import HTTPClient
from deal_watcher.database.repository import DealRepository
from deal_watcher.scrapers.auto_scraper import AutoScraper
from deal_watcher.scrapers.reality_scraper import RealityScraper
from deal_watcher.filters.auto_filter import AutoFilter
from deal_watcher.filters.reality_filter import RealityFilter

# Load environment variables
load_dotenv()

logger = None


def load_config(config_path: str = 'deal_watcher/config/config.json') -> Dict[str, Any]:
    """
    Load configuration from JSON file.

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


def get_scraper(scraper_config: Dict[str, Any], http_client: HTTPClient):
    """
    Factory function to create appropriate scraper based on type.

    Args:
        scraper_config: Scraper configuration
        http_client: HTTP client instance

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
    Factory function to create appropriate filter based on type.

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


def process_scraper(
    scraper_config: Dict[str, Any],
    http_client: HTTPClient,
    repository: DealRepository
) -> Dict[str, int]:
    """
    Process a single scraper configuration.

    Args:
        scraper_config: Scraper configuration
        http_client: HTTP client instance
        repository: Database repository

    Returns:
        Dictionary with statistics
    """
    name = scraper_config.get('name', 'Unknown')
    category_id = scraper_config.get('category_id')

    logger.info(f"=" * 60)
    logger.info(f"Starting scraper: {name}")
    logger.info(f"=" * 60)

    # Create scraping run
    run = repository.create_scraping_run(category_id)

    stats = {
        'listings_processed': 0,
        'new_deals_found': 0,
        'price_changes_detected': 0,
        'matches_found': 0
    }

    try:
        # Initialize scraper and filter
        scraper = get_scraper(scraper_config, http_client)
        listing_filter = get_filter(scraper_config)

        # Scrape listings
        listings = scraper.run()
        stats['listings_processed'] = len(listings)

        logger.info(f"Processing {len(listings)} listings...")

        # Process each listing
        for listing in listings:
            try:
                # Quick filter on list data
                if not listing_filter.matches(listing, detailed=False):
                    continue

                # Fetch detailed data if it passes quick filter
                external_id = listing.get('external_id')
                detail_url = listing.get('url')

                logger.info(f"Fetching details for listing {external_id}")
                detail_data = scraper.scrape_detail_page(detail_url)

                if detail_data:
                    # Merge detail data into listing
                    listing.update(detail_data)

                    # Apply detailed filter
                    if not listing_filter.matches(listing, detailed=True):
                        continue

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

        logger.info(f"Scraper '{name}' completed:")
        logger.info(f"  - Listings processed: {stats['listings_processed']}")
        logger.info(f"  - Matches found: {stats['matches_found']}")
        logger.info(f"  - New deals: {stats['new_deals_found']}")
        logger.info(f"  - Price changes: {stats['price_changes_detected']}")

        return stats

    except Exception as e:
        error_msg = f"Error in scraper '{name}': {e}"
        logger.error(error_msg)
        repository.update_scraping_run(
            run.id,
            status='failed',
            error_message=str(e)
        )
        return stats


def main():
    """Main entry point."""
    global logger

    # Setup logger
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    logger = setup_logger('deal_watcher', level=log_level)

    logger.info("=" * 60)
    logger.info("Deal Watcher - Starting")
    logger.info("=" * 60)

    # Load configuration
    config = load_config()

    # Initialize HTTP client
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
        'new_deals_found': 0,
        'price_changes_detected': 0,
        'matches_found': 0
    }

    scrapers = config.get('scrapers', [])
    enabled_scrapers = [s for s in scrapers if s.get('enabled', True)]

    logger.info(f"Found {len(enabled_scrapers)} enabled scrapers")

    for scraper_config in enabled_scrapers:
        stats = process_scraper(scraper_config, http_client, repository)

        # Accumulate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    # Clean up
    http_client.close()

    # Print summary
    logger.info("=" * 60)
    logger.info("Deal Watcher - Complete")
    logger.info("=" * 60)
    logger.info(f"Total listings processed: {total_stats['listings_processed']}")
    logger.info(f"Total matches found: {total_stats['matches_found']}")
    logger.info(f"Total new deals: {total_stats['new_deals_found']}")
    logger.info(f"Total price changes: {total_stats['price_changes_detected']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
