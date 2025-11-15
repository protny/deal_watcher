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
        self.reject_price_per_m2 = filter_config.get('reject_price_per_m2', True)  # Default True

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
            # Reject suspiciously low prices (likely per-m² prices)
            if self.reject_price_per_m2 and price < 100:
                logger.debug(f"Listing {listing.get('external_id')} rejected: suspiciously low price {price} EUR (likely per-m²)")
                return False

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
        Extract land area from text, distinguishing from floor area.

        For houses, there are typically TWO areas:
        - Floor area (podlahová plocha, úžitková plocha, zastavená plocha) - smaller
        - Land area (pozemok, parcela) - larger, this is what we want

        Args:
            text: Text to extract area from

        Returns:
            Land area in square meters or None if not found
        """
        if not text:
            return None

        normalized_text = text.lower()

        # Keywords indicating LAND area (good)
        land_keywords = ['pozemok', 'parcela', 'pozemku', 'parcely', 'land', 'ha', 'hektár']

        # Keywords indicating FLOOR area (bad - ignore these)
        floor_keywords = ['podlahov', 'užitkov', 'zastaven', 'obytná', 'floor', 'úžitkov']

        # Comprehensive pattern for area with context (60 chars before and after)
        # This captures: "pozemok 5000 m2" or "úžitková plocha 120 m²"
        # Number pattern matches: "5", "50000", "50 000", "4.2", "4,5"
        # Note: .{0,60}? is non-greedy to avoid consuming digits from the number
        # Groups: (1) context before, (2) number, (3) unit, (4) context after
        pattern = r'(.{0,60}?)(\d+(?:[\s,]\d+)*(?:[.,]\d+)?)\s*(m2|m²|metrov\s*štvorcových|metrov|ha|hektár|hektárov|árov|arov|ár|a)(.{0,60})'

        land_areas = []
        all_areas = []

        for match in re.finditer(pattern, normalized_text, re.IGNORECASE):
            try:
                context_before = match.group(1).lower()
                unit = match.group(3).lower()
                context_after = match.group(4).lower()
                context = context_before + ' ' + context_after

                # Extract number
                number_str = match.group(2).replace(' ', '').replace(',', '.')
                value = float(number_str)

                # Convert to m² based on unit
                if 'ha' in unit or 'hektár' in unit:
                    area_m2 = value * 10000
                elif 'ár' in unit and 'hektár' not in unit:
                    area_m2 = value * 100
                else:
                    area_m2 = value

                # Check if this is land or floor area based on context
                is_land = any(kw in context for kw in land_keywords)
                is_floor = any(kw in context for kw in floor_keywords)

                logger.debug(f"Found area: {area_m2} m² (land={is_land}, floor={is_floor}, context: ...{context_before[-30:]}...{context_after[:30]}...)")

                all_areas.append(area_m2)

                if is_land and not is_floor:
                    land_areas.append(area_m2)
                elif not is_floor:
                    # No clear indicators, could be land
                    land_areas.append(area_m2)

            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing area: {e}")
                continue

        # Return the largest land area found
        if land_areas:
            max_land = max(land_areas)
            logger.debug(f"Selected land area: {max_land} m² from {len(land_areas)} candidates")
            return max_land
        elif all_areas:
            # No clear land area, return largest overall (might be mislabeled)
            max_area = max(all_areas)
            if max_area > 5000:  # If > 5000 m², probably land even if not labeled
                logger.debug(f"No clear land area, but found large area: {max_area} m² (probably land)")
                return max_area
            else:
                logger.debug(f"Only found small area: {max_area} m² (probably floor area)")
                return None

        return None
