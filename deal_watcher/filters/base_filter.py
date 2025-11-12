"""Base filter abstract class."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class BaseFilter(ABC):
    """Abstract base class for all filters."""

    def __init__(self, filter_config: Dict[str, Any]):
        """
        Initialize base filter.

        Args:
            filter_config: Filter configuration dictionary
        """
        self.config = filter_config

    @abstractmethod
    def matches(self, listing: Dict[str, Any], detailed: bool = False) -> bool:
        """
        Check if a listing matches the filter criteria.

        Args:
            listing: Listing data dictionary
            detailed: Whether this is detailed data (from detail page)

        Returns:
            True if listing matches criteria, False otherwise
        """
        pass

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison (lowercase, remove extra whitespace).

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        if not text:
            return ''
        return ' '.join(text.lower().strip().split())

    def _text_contains_any(self, text: str, keywords: list) -> bool:
        """
        Check if text contains any of the keywords.

        Args:
            text: Text to search
            keywords: List of keywords

        Returns:
            True if any keyword is found
        """
        if not text or not keywords:
            return False

        normalized_text = self._normalize_text(text)

        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            if normalized_keyword in normalized_text:
                return True

        return False

    def _text_contains_all(self, text: str, keywords: list) -> bool:
        """
        Check if text contains all of the keywords.

        Args:
            text: Text to search
            keywords: List of keywords

        Returns:
            True if all keywords are found
        """
        if not keywords:
            return True

        if not text:
            return False

        normalized_text = self._normalize_text(text)

        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            if normalized_keyword not in normalized_text:
                return False

        return True

    def _text_excludes_all(self, text: str, keywords: list) -> bool:
        """
        Check if text excludes all of the keywords (none are present).

        Args:
            text: Text to search
            keywords: List of keywords to exclude

        Returns:
            True if none of the keywords are found
        """
        if not keywords:
            return True

        if not text:
            return True

        normalized_text = self._normalize_text(text)

        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            if normalized_keyword in normalized_text:
                return False

        return True
