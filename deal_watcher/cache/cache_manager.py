"""File system cache manager for storing scraped listings."""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


def _convert_datetimes_to_str(data: Any) -> Any:
    """
    Recursively convert datetime objects to ISO format strings for JSON serialization.

    Args:
        data: Data to convert (can be dict, list, datetime, or any other type)

    Returns:
        Data with datetime objects converted to strings
    """
    if isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, dict):
        return {key: _convert_datetimes_to_str(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_convert_datetimes_to_str(item) for item in data]
    else:
        return data


class CacheManager:
    """Manages file system cache for scraped listings."""

    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Root directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cache manager initialized at {self.cache_dir.absolute()}")

    def _get_listing_dir(self, source: str, category: str, listing_id: str) -> Path:
        """
        Get directory path for a listing.

        Args:
            source: Source website (e.g., 'bazos')
            category: Category (e.g., 'auto', 'reality')
            listing_id: External listing ID

        Returns:
            Path to listing directory
        """
        listing_dir = self.cache_dir / source / category / listing_id
        listing_dir.mkdir(parents=True, exist_ok=True)
        return listing_dir

    def _generate_filename(self, timestamp: Optional[datetime] = None) -> str:
        """
        Generate filename with timestamp.

        Args:
            timestamp: Timestamp to use (default: now)

        Returns:
            Filename in format: YYYY-MM-DD_HHMMSS.json
        """
        if timestamp is None:
            timestamp = datetime.now()
        return timestamp.strftime("%Y-%m-%d_%H%M%S.json")

    def _extract_listing_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract listing ID from URL.

        Args:
            url: Full URL to listing

        Returns:
            Listing ID or None
        """
        # For Bazos: /inzerat/123456789/title or /123456789.htm
        patterns = [
            r'/inzerat/(\d+)/',
            r'/(\d+)\.htm',
            r'/(\d+)$'
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        logger.warning(f"Could not extract listing ID from URL: {url}")
        return None

    def save_listing(
        self,
        source: str,
        category: str,
        listing_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Optional[Path]:
        """
        Save listing data to cache.

        Args:
            source: Source website (e.g., 'bazos')
            category: Category (e.g., 'auto', 'reality')
            listing_data: Dictionary containing listing data (must have 'url' or 'external_id')
            timestamp: Timestamp for the cache file (default: now)

        Returns:
            Path to saved file or None on error
        """
        # Get listing ID
        listing_id = listing_data.get('external_id')
        if not listing_id and 'url' in listing_data:
            listing_id = self._extract_listing_id_from_url(listing_data['url'])

        if not listing_id:
            logger.error("Cannot save listing: no external_id or parseable URL")
            return None

        # Get listing directory
        listing_dir = self._get_listing_dir(source, category, listing_id)

        # Generate filename
        filename = self._generate_filename(timestamp)
        filepath = listing_dir / filename

        # Convert datetime objects to strings for JSON serialization
        serializable_data = _convert_datetimes_to_str(listing_data)

        # Add metadata
        cache_data = {
            'cached_at': (timestamp or datetime.now()).isoformat(),
            'source': source,
            'category': category,
            'listing_id': listing_id,
            'data': serializable_data
        }

        # Save to file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved listing {listing_id} to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving listing to cache: {e}")
            return None

    def get_latest_listing(
        self,
        source: str,
        category: str,
        listing_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the latest cached version of a listing.

        Args:
            source: Source website
            category: Category
            listing_id: Listing ID

        Returns:
            Cached listing data or None if not found
        """
        listing_dir = self._get_listing_dir(source, category, listing_id)

        if not listing_dir.exists():
            return None

        # Get all cache files, sorted by name (which sorts by timestamp)
        cache_files = sorted(listing_dir.glob("*.json"), reverse=True)

        if not cache_files:
            return None

        # Read the latest file
        latest_file = cache_files[0]
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            logger.debug(f"Retrieved cached listing {listing_id} from {latest_file}")
            return cache_data
        except Exception as e:
            logger.error(f"Error reading cached listing: {e}")
            return None

    def get_listing_history(
        self,
        source: str,
        category: str,
        listing_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all cached versions of a listing (history).

        Args:
            source: Source website
            category: Category
            listing_id: Listing ID

        Returns:
            List of cached versions, newest first
        """
        listing_dir = self._get_listing_dir(source, category, listing_id)

        if not listing_dir.exists():
            return []

        # Get all cache files, sorted by name (newest first)
        cache_files = sorted(listing_dir.glob("*.json"), reverse=True)

        history = []
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                history.append(cache_data)
            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {e}")

        return history

    def has_listing(self, source: str, category: str, listing_id: str) -> bool:
        """
        Check if a listing exists in cache.

        Args:
            source: Source website
            category: Category
            listing_id: Listing ID

        Returns:
            True if cached, False otherwise
        """
        listing_dir = self._get_listing_dir(source, category, listing_id)
        return listing_dir.exists() and any(listing_dir.glob("*.json"))

    def detect_changes(
        self,
        source: str,
        category: str,
        listing_id: str,
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare new data with latest cached version to detect changes.

        Args:
            source: Source website
            category: Category
            listing_id: Listing ID
            new_data: New listing data to compare

        Returns:
            Dictionary with 'changed' (bool) and 'differences' (dict) keys
        """
        latest = self.get_latest_listing(source, category, listing_id)

        if not latest:
            return {'changed': True, 'differences': {'reason': 'new_listing'}}

        old_data = latest.get('data', {})
        differences = {}

        # Check important fields
        fields_to_check = ['title', 'description', 'price', 'location']

        for field in fields_to_check:
            old_value = old_data.get(field)
            new_value = new_data.get(field)

            if old_value != new_value:
                differences[field] = {
                    'old': old_value,
                    'new': new_value
                }

        changed = len(differences) > 0

        if changed:
            logger.info(f"Detected changes in listing {listing_id}: {list(differences.keys())}")

        return {
            'changed': changed,
            'differences': differences
        }

    def get_all_cached_listings(
        self,
        source: str,
        category: str
    ) -> List[str]:
        """
        Get list of all cached listing IDs for a source/category.

        Args:
            source: Source website
            category: Category

        Returns:
            List of listing IDs
        """
        category_dir = self.cache_dir / source / category

        if not category_dir.exists():
            return []

        # Get all subdirectories (each is a listing ID)
        listing_ids = [d.name for d in category_dir.iterdir() if d.is_dir()]
        return listing_ids

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        stats = {
            'total_sources': 0,
            'total_categories': 0,
            'total_listings': 0,
            'total_files': 0,
            'sources': {}
        }

        if not self.cache_dir.exists():
            return stats

        for source_dir in self.cache_dir.iterdir():
            if not source_dir.is_dir():
                continue

            stats['total_sources'] += 1
            source_name = source_dir.name
            stats['sources'][source_name] = {
                'categories': {},
                'total_listings': 0
            }

            for category_dir in source_dir.iterdir():
                if not category_dir.is_dir():
                    continue

                stats['total_categories'] += 1
                category_name = category_dir.name

                listing_count = 0
                file_count = 0

                for listing_dir in category_dir.iterdir():
                    if not listing_dir.is_dir():
                        continue

                    listing_count += 1
                    files = list(listing_dir.glob("*.json"))
                    file_count += len(files)

                stats['sources'][source_name]['categories'][category_name] = {
                    'listings': listing_count,
                    'files': file_count
                }
                stats['sources'][source_name]['total_listings'] += listing_count
                stats['total_listings'] += listing_count
                stats['total_files'] += file_count

        return stats
