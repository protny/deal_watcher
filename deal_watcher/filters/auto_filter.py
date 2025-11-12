"""Auto filter for BMW vehicles."""

from typing import Dict, Any

from deal_watcher.filters.base_filter import BaseFilter
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class AutoFilter(BaseFilter):
    """Filter for auto listings (BMW vehicles)."""

    def __init__(self, filter_config: Dict[str, Any]):
        """
        Initialize auto filter.

        Args:
            filter_config: Filter configuration
        """
        super().__init__(filter_config)

        # Extract filter criteria
        self.keywords_any = filter_config.get('keywords_any', [])  # Model: E36, E46, E39
        self.keywords_all = filter_config.get('keywords_all', [])  # benzin, manuál
        self.keywords_engine = filter_config.get('keywords_engine', [])  # 6 valec, etc.
        self.keywords_excluded = filter_config.get('keywords_excluded', [])
        self.price_min = filter_config.get('price_min')
        self.price_max = filter_config.get('price_max')

    def matches(self, listing: Dict[str, Any], detailed: bool = False) -> bool:
        """
        Check if listing matches BMW filter criteria.

        Args:
            listing: Listing data
            detailed: Whether this is detailed data

        Returns:
            True if listing matches all criteria
        """
        title = listing.get('title', '')
        description = listing.get('description', '')
        combined_text = f"{title} {description}"

        # Check if any model keyword matches (E36, E46, E39)
        if self.keywords_any:
            if not self._text_contains_any(combined_text, self.keywords_any):
                logger.debug(f"Listing {listing.get('external_id')} rejected: no model match")
                return False

        # Check if all required keywords are present (benzin, manuál)
        if self.keywords_all:
            if not self._text_contains_all(combined_text, self.keywords_all):
                logger.debug(f"Listing {listing.get('external_id')} rejected: missing required keywords")
                return False

        # Check if at least one engine keyword is present (6 valec, etc.)
        if self.keywords_engine:
            if not self._text_contains_any(combined_text, self.keywords_engine):
                logger.debug(f"Listing {listing.get('external_id')} rejected: no engine match")
                return False

        # Check excluded keywords
        if self.keywords_excluded:
            if not self._text_excludes_all(combined_text, self.keywords_excluded):
                logger.debug(f"Listing {listing.get('external_id')} rejected: contains excluded keyword")
                return False

        # Check price range
        price = listing.get('price')
        if price is not None:
            if self.price_min is not None and price < self.price_min:
                logger.debug(f"Listing {listing.get('external_id')} rejected: price too low")
                return False

            if self.price_max is not None and price > self.price_max:
                logger.debug(f"Listing {listing.get('external_id')} rejected: price too high")
                return False

        logger.info(f"Listing {listing.get('external_id')} MATCHES filter criteria")
        return True
