"""
Downloader script - fetches and caches HTML pages from configured URLs.

This script only downloads and stores raw HTML pages. No filtering or processing.
Run this periodically to build/update your local cache of listings.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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


def save_page_to_cache(
    cache_dir: Path,
    url: str,
    content: bytes,
    page_number: int
) -> Path:
    """
    Save HTML page to cache directory.

    Args:
        cache_dir: Cache directory for this URL category
        url: URL that was fetched
        content: Raw HTML content
        page_number: Page number

    Returns:
        Path to saved file
    """
    # Create filename: page_0001.html, page_0002.html, etc.
    filename = f"page_{page_number:04d}.html"
    filepath = cache_dir / filename

    # Save HTML
    with open(filepath, 'wb') as f:
        f.write(content)

    # Save metadata
    meta_filename = f"page_{page_number:04d}.meta.json"
    meta_filepath = cache_dir / meta_filename
    metadata = {
        'url': url,
        'page_number': page_number,
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
    Download all pages for a single URL category.

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

    stats = {
        'pages_downloaded': 0,
        'pages_failed': 0,
        'total_bytes': 0
    }

    # Download each page
    for page_num in range(max_pages):
        url = get_page_url(base_url, page_num)
        logger.info(f"Downloading page {page_num + 1}/{max_pages}: {url}")

        try:
            response = http_client.get(url)
            if response and response.status_code == 200:
                content = response.content

                # Check if page is empty or has no listings
                if len(content) < 1000:
                    logger.warning(f"Page {page_num + 1} seems empty, stopping")
                    break

                # Save to cache
                filepath = save_page_to_cache(cache_dir, url, content, page_num)
                stats['pages_downloaded'] += 1
                stats['total_bytes'] += len(content)

                logger.info(f"  ✓ Saved to {filepath} ({len(content):,} bytes)")

            else:
                logger.error(f"  ✗ Failed to download page {page_num + 1}")
                stats['pages_failed'] += 1

                # If we fail on page 0, something is wrong - stop
                if page_num == 0:
                    logger.error("Failed on first page, stopping this category")
                    break

        except Exception as e:
            logger.error(f"Error downloading page {page_num + 1}: {e}")
            stats['pages_failed'] += 1

    logger.info(f"\n{name} completed:")
    logger.info(f"  - Pages downloaded: {stats['pages_downloaded']}")
    logger.info(f"  - Pages failed: {stats['pages_failed']}")
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
        'pages_downloaded': 0,
        'pages_failed': 0,
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
    logger.info(f"Total pages downloaded: {total_stats['pages_downloaded']}")
    logger.info(f"Total pages failed: {total_stats['pages_failed']}")
    logger.info(f"Total size: {total_stats['total_bytes'] / 1024 / 1024:.2f} MB")
    logger.info(f"Cache location: {base_cache_dir.absolute()}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
