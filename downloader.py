"""
Downloader script - fetches and caches individual listing HTML pages.

This script:
1. Fetches list pages (not cached)
2. Extracts individual listing URLs
3. Downloads and caches each listing's detail page as separate HTML file
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from deal_watcher.utils.logger import setup_logger, get_logger
from deal_watcher.utils.http_client import HTTPClient

logger = None


def load_download_config(config_path: str = 'download_config.json') -> Dict[str, Any]:
    """
    Load download configuration.

    Args:
        config_path: Path to download configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)


def get_page_url(base_url: str, page_number: int) -> str:
    """
    Get URL for a specific page number (Bazos.sk format).

    Args:
        base_url: Base URL of the category
        page_number: Page number (0-indexed)

    Returns:
        Full URL for the page
    """
    if page_number == 0:
        return base_url

    offset = page_number * 20  # Bazos has 20 listings per page
    base_url = base_url.rstrip('/')
    return f"{base_url}/{offset}/"


def extract_base_url(url: str) -> str:
    """Extract base URL from full URL."""
    match = re.match(r'(https?://[^/]+)', url)
    return match.group(1) if match else url


def extract_listing_urls_from_page(html_content: bytes, base_url: str) -> List[Dict[str, str]]:
    """
    Extract listing URLs from a list page.

    Args:
        html_content: Raw HTML content
        base_url: Base URL for resolving relative links

    Returns:
        List of dicts with listing_id and url
    """
    soup = BeautifulSoup(html_content, 'lxml')
    listings = []

    # Find all listing containers
    listing_divs = soup.find_all('div', class_='inzeraty')

    for listing_div in listing_divs:
        try:
            # Find title and URL
            title_h2 = listing_div.find('h2', class_='nadpis')
            if not title_h2:
                continue

            title_link = title_h2.find('a')
            if not title_link:
                continue

            relative_url = title_link.get('href', '')
            full_url = urljoin(base_url, relative_url)

            # Extract listing ID from URL
            # Pattern: /inzerat/123456789/title
            match = re.search(r'/inzerat/(\d+)/', full_url)
            if match:
                listing_id = match.group(1)
                listings.append({
                    'listing_id': listing_id,
                    'url': full_url
                })

        except Exception as e:
            logger.warning(f"Error parsing listing: {e}")
            continue

    return listings


def save_listing_to_cache(
    cache_dir: Path,
    listing_id: str,
    url: str,
    content: bytes
) -> Path:
    """
    Save individual listing HTML to cache directory.

    Args:
        cache_dir: Cache directory for this URL category
        listing_id: Listing ID
        url: URL that was fetched
        content: Raw HTML content

    Returns:
        Path to saved file
    """
    # Create filename: {listing_id}.html
    filename = f"{listing_id}.html"
    filepath = cache_dir / filename

    # Save HTML
    with open(filepath, 'wb') as f:
        f.write(content)

    # Save metadata
    meta_filename = f"{listing_id}.meta.json"
    meta_filepath = cache_dir / meta_filename
    metadata = {
        'listing_id': listing_id,
        'url': url,
        'downloaded_at': datetime.now().isoformat(),
        'content_length': len(content)
    }
    with open(meta_filepath, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    return filepath


def download_url_category(
    url_config: Dict[str, Any],
    http_client: HTTPClient,
    base_cache_dir: Path
) -> Dict[str, int]:
    """
    Download all individual listings for a URL category.

    Args:
        url_config: URL configuration (name, base_url, max_pages, cache_subdir)
        http_client: HTTP client instance
        base_cache_dir: Base cache directory (e.g., cache/bazos)

    Returns:
        Statistics dictionary
    """
    name = url_config['name']
    base_url = url_config['base_url']
    max_pages = url_config['max_pages']
    cache_subdir = url_config['cache_subdir']

    logger.info(f"=" * 60)
    logger.info(f"Downloading: {name}")
    logger.info(f"URL: {base_url}")
    logger.info(f"Max pages: {max_pages}")
    logger.info(f"=" * 60)

    # Create cache directory
    cache_dir = base_cache_dir / cache_subdir
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Cache directory: {cache_dir}")

    # Get already cached listing IDs (to avoid re-downloading)
    cached_ids = set()
    for html_file in cache_dir.glob('*.html'):
        listing_id = html_file.stem
        cached_ids.add(listing_id)

    logger.info(f"Found {len(cached_ids)} already cached listings")

    stats = {
        'list_pages_fetched': 0,
        'listings_found': 0,
        'listings_downloaded': 0,
        'listings_skipped': 0,
        'listings_failed': 0,
        'total_bytes': 0
    }

    base_domain = extract_base_url(base_url)
    all_listing_urls = []

    # Step 1: Fetch list pages and extract listing URLs
    logger.info("Step 1: Extracting listing URLs from list pages...")
    for page_num in range(max_pages):
        url = get_page_url(base_url, page_num)
        logger.info(f"Fetching list page {page_num + 1}/{max_pages}")

        try:
            response = http_client.get(url)
            if response and response.status_code == 200:
                content = response.content
                stats['list_pages_fetched'] += 1

                # Extract listing URLs
                listings = extract_listing_urls_from_page(content, base_domain)
                logger.info(f"  Found {len(listings)} listings on page {page_num + 1}")

                all_listing_urls.extend(listings)

                if len(listings) == 0:
                    logger.warning(f"No listings on page {page_num + 1}, stopping")
                    break

            else:
                logger.error(f"  Failed to fetch page {page_num + 1}")
                if page_num == 0:
                    logger.error("Failed on first page, stopping this category")
                    break

        except Exception as e:
            logger.error(f"Error fetching page {page_num + 1}: {e}")

    stats['listings_found'] = len(all_listing_urls)
    logger.info(f"\nFound {len(all_listing_urls)} total listings")

    # Step 2: Download individual listing pages
    logger.info("\nStep 2: Downloading individual listing pages...")
    for idx, listing_info in enumerate(all_listing_urls, 1):
        listing_id = listing_info['listing_id']
        listing_url = listing_info['url']

        # Skip if already cached
        if listing_id in cached_ids:
            stats['listings_skipped'] += 1
            logger.debug(f"[{idx}/{len(all_listing_urls)}] Skipping cached: {listing_id}")
            continue

        logger.info(f"[{idx}/{len(all_listing_urls)}] Downloading: {listing_id}")

        try:
            response = http_client.get(listing_url)
            if response and response.status_code == 200:
                content = response.content

                # Save to cache
                filepath = save_listing_to_cache(cache_dir, listing_id, listing_url, content)
                stats['listings_downloaded'] += 1
                stats['total_bytes'] += len(content)

                logger.info(f"  ✓ Saved {listing_id} ({len(content):,} bytes)")

            else:
                logger.error(f"  ✗ Failed to download {listing_id}")
                stats['listings_failed'] += 1

        except Exception as e:
            logger.error(f"Error downloading {listing_id}: {e}")
            stats['listings_failed'] += 1

    logger.info(f"\n{name} completed:")
    logger.info(f"  - List pages fetched: {stats['list_pages_fetched']}")
    logger.info(f"  - Listings found: {stats['listings_found']}")
    logger.info(f"  - Listings downloaded: {stats['listings_downloaded']}")
    logger.info(f"  - Listings skipped (cached): {stats['listings_skipped']}")
    logger.info(f"  - Listings failed: {stats['listings_failed']}")
    logger.info(f"  - Total size: {stats['total_bytes'] / 1024 / 1024:.2f} MB")

    return stats


def main():
    """Main entry point for downloader."""
    global logger

    # Setup logger
    logger = setup_logger('downloader', level='INFO')

    logger.info("=" * 60)
    logger.info("Deal Watcher - Downloader")
    logger.info("=" * 60)

    # Load configuration
    config = load_download_config()

    # Setup HTTP client
    download_settings = config.get('download_settings', {})
    http_client = HTTPClient(
        timeout=download_settings.get('timeout_seconds', 30),
        max_retries=download_settings.get('max_retries', 3),
        backoff_factor=download_settings.get('retry_backoff_factor', 2.0),
        request_delay=download_settings.get('request_delay_seconds', 2.5),
        user_agents=download_settings.get('user_agents', [])
    )

    # Base cache directory
    base_cache_dir = Path('cache/bazos')
    base_cache_dir.mkdir(parents=True, exist_ok=True)

    # Process each URL category
    total_stats = {
        'list_pages_fetched': 0,
        'listings_found': 0,
        'listings_downloaded': 0,
        'listings_skipped': 0,
        'listings_failed': 0,
        'total_bytes': 0
    }

    url_configs = config.get('urls_to_download', [])
    logger.info(f"Found {len(url_configs)} URL categories to download\n")

    for url_config in url_configs:
        stats = download_url_category(url_config, http_client, base_cache_dir)

        # Accumulate stats
        for key in total_stats:
            total_stats[key] += stats.get(key, 0)

    # Clean up
    http_client.close()

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Download Complete")
    logger.info("=" * 60)
    logger.info(f"Total list pages fetched: {total_stats['list_pages_fetched']}")
    logger.info(f"Total listings found: {total_stats['listings_found']}")
    logger.info(f"Total listings downloaded: {total_stats['listings_downloaded']}")
    logger.info(f"Total listings skipped (cached): {total_stats['listings_skipped']}")
    logger.info(f"Total listings failed: {total_stats['listings_failed']}")
    logger.info(f"Total size: {total_stats['total_bytes'] / 1024 / 1024:.2f} MB")
    logger.info(f"Cache location: {base_cache_dir.absolute()}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
