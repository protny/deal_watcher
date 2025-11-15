"""Auto scraper for BMW vehicles on Bazos.sk."""

from typing import Dict, Any

from deal_watcher.scrapers.bazos_scraper import BazosScraper
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class AutoScraper(BazosScraper):
    """
    Scraper for auto listings on Bazos.sk.

    Inherits all functionality from BazosScraper since the HTML structure
    is identical across different Bazos.sk categories.
    """

    def __init__(self, config: Dict[str, Any], http_client, cache_manager=None):
        """
        Initialize auto scraper.

        Args:
            config: Scraper configuration
            http_client: HTTP client instance
            cache_manager: Optional CacheManager instance
        """
        super().__init__(config, http_client, cache_manager)
        logger.info(f"Initialized AutoScraper for: {self.name}")
