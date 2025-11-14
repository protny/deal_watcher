"""Reality filter for land/houses/cottages."""

import re
from typing import Dict, Any, Optional

from deal_watcher.filters.base_filter import BaseFilter
from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class RealityFilter(BaseFilter):
    """Filter for reality listings (land, houses, cottages)."""

    def __init__(self, filter_config: Dict[str, Any]):
        """
        Initialize reality filter.

        Args:
            filter_config: Filter configuration
        """
        super().__init__(filter_config)

        # Extract filter criteria
        self.price_max = filter_config.get('price_max')
        self.price_min = filter_config.get('price_min')
        self.area_min = filter_config.get('area_min', 40000)  # Default 40000 m²
        self.area_units = filter_config.get('area_units', ['m2', 'm²', 'ha', 'hektár'])
        self.keywords_excluded = filter_config.get('keywords_excluded', [])

    def matches(self, listing: Dict[str, Any], detailed: bool = False) -> bool:
        """
        Check if listing matches reality filter criteria.

        Args:
            listing: Listing data
            detailed: Whether this is detailed data (full description available)

        Returns:
            True if listing matches all criteria
        """
        title = listing.get('title', '')
        description = listing.get('description', '')
        combined_text = f"{title} {description}"

        # QUICK FILTER (detailed=False): Only check price
        # Don't try to extract area from truncated description - it's often missing
        if not detailed:
            # Check price range (this IS reliably on list page)
            price = listing.get('price')
            if price is not None:
                if self.price_min is not None and price < self.price_min:
                    logger.debug(f"Listing {listing.get('external_id')} quick-rejected: price too low")
                    return False

                if self.price_max is not None and price > self.price_max:
                    logger.debug(f"Listing {listing.get('external_id')} quick-rejected: price {price} > {self.price_max}")
                    return False

            # Pass quick filter - fetch detail page to check area
            logger.debug(f"Listing {listing.get('external_id')} passed quick filter")
            return True

        # FULL FILTER (detailed=True): Check everything in full description
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
                logger.debug(f"Listing {listing.get('external_id')} rejected: price {price} > {self.price_max}")
                return False

        # Check area (now from FULL description)
        area = self._extract_area(combined_text)
        if area is None:
            logger.debug(f"Listing {listing.get('external_id')} rejected: could not extract area")
            return False

        if area < self.area_min:
            logger.debug(f"Listing {listing.get('external_id')} rejected: area {area} m² < {self.area_min} m²")
            return False

        logger.info(f"Listing {listing.get('external_id')} MATCHES filter criteria (area: {area} m², price: {price})")
        return True

    def _extract_area(self, text: str) -> Optional[float]:
        """
        Extract area from text and convert to square meters.

        Args:
            text: Text to extract area from

        Returns:
            Area in square meters or None if not found
        """
        if not text:
            return None

        normalized_text = text.lower()

        # Patterns for area extraction
        patterns = [
            # Square meters: "1000 m2", "1 000 m²", "1000m2", "1000 metrov"
            r'(\d+[\s,]*\d*)\s*(?:m2|m²|metrov\s*štvorcových|metrov)',
            # Hectares: "4 ha", "4,5 hektárov", "4.5 hektár"
            r'(\d+[,.]?\d*)\s*(?:ha|hektár|hektárov)',
            # Ares: "400 árov", "400a"
            r'(\d+[\s,]*\d*)\s*(?:árov|arov|á)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, normalized_text, re.IGNORECASE)

            for match in matches:
                try:
                    # Extract number part
                    number_str = match.group(1)
                    # Remove spaces and replace comma with dot
                    number_str = number_str.replace(' ', '').replace(',', '.')
                    value = float(number_str)

                    # Check which unit was matched
                    unit = match.group(0).lower()

                    if 'ha' in unit or 'hektár' in unit:
                        # Convert hectares to m² (1 ha = 10,000 m²)
                        area_m2 = value * 10000
                        logger.debug(f"Extracted area: {value} ha = {area_m2} m²")
                        return area_m2
                    elif 'ár' in unit or 'a' in unit:
                        # Convert ares to m² (1 are = 100 m²)
                        area_m2 = value * 100
                        logger.debug(f"Extracted area: {value} árov = {area_m2} m²")
                        return area_m2
                    else:
                        # Already in square meters
                        logger.debug(f"Extracted area: {value} m²")
                        return value

                except (ValueError, IndexError) as e:
                    logger.debug(f"Error parsing area: {e}")
                    continue

        return None
