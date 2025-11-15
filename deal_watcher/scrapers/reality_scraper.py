"""Reality scraper for land/houses/cottages on Bazos.sk."""

from typing import Dict, Any

from deal_watcher.scrapers.bazos_scraper import BazosScraper
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class RealityScraper(BazosScraper):
    """
    Scraper for reality listings on Bazos.sk (land, houses, cottages).

    Inherits all functionality from BazosScraper since the HTML structure
    is identical across different Bazos.sk categories.
    """

    def __init__(self, config: Dict[str, Any], http_client, cache_manager=None):
        """
        Initialize reality scraper.

        Args:
            config: Scraper configuration
            http_client: HTTP client instance
            cache_manager: Optional CacheManager instance
        """
        super().__init__(config, http_client, cache_manager)
        logger.info(f"Initialized RealityScraper for: {self.name}")
