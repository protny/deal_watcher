"""Test script to verify all imports work correctly."""

import sys

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        # Test utilities
        from deal_watcher.utils.logger import setup_logger, get_logger
        from deal_watcher.utils.http_client import HTTPClient
        print("✓ Utils imports OK")

        # Test database
        from deal_watcher.database.models import Category, Deal, PriceHistory, DealImage, ScrapingRun
        from deal_watcher.database.repository import DealRepository
        print("✓ Database imports OK")

        # Test scrapers
        from deal_watcher.scrapers.base_scraper import BaseScraper
        from deal_watcher.scrapers.bazos_scraper import BazosScraper
        from deal_watcher.scrapers.auto_scraper import AutoScraper
        from deal_watcher.scrapers.reality_scraper import RealityScraper
        print("✓ Scraper imports OK")

        # Test filters
        from deal_watcher.filters.base_filter import BaseFilter
        from deal_watcher.filters.auto_filter import AutoFilter
        from deal_watcher.filters.reality_filter import RealityFilter
        print("✓ Filter imports OK")

        # Test main
        from deal_watcher.main import load_config, get_scraper, get_filter
        print("✓ Main imports OK")

        print("\n✓ All imports successful!")
        return True

    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        return False

if __name__ == '__main__':
    success = test_imports()
    sys.exit(0 if success else 1)
