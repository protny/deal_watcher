"""HTTP client with retry logic and rate limiting."""

import time
import random
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from deal_watcher.utils.logger import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """HTTP client with retry logic and user-agent rotation."""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        request_delay: float = 2.5,
        user_agents: Optional[list] = None
    ):
        """
        Initialize HTTP client.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff multiplier for retries
            request_delay: Delay between requests in seconds
            user_agents: List of user agent strings for rotation
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.request_delay = request_delay
        self.user_agents = user_agents or [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        ]
        self.last_request_time = 0
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create requests session with retry strategy.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_random_user_agent(self) -> str:
        """
        Get random user agent from the list.

        Returns:
            Random user agent string
        """
        return random.choice(self.user_agents)

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        skip_rate_limit: bool = False
    ) -> Optional[requests.Response]:
        """
        Perform GET request with retry logic.

        Args:
            url: URL to request
            params: Query parameters
            headers: Additional headers
            skip_rate_limit: Skip rate limiting for this request

        Returns:
            Response object or None if request failed
        """
        if not skip_rate_limit:
            self._rate_limit()

        # Prepare headers
        request_headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'sk,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        if headers:
            request_headers.update(headers)

        try:
            logger.debug(f"GET request: {url}")
            response = self.session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug(f"Response status: {response.status_code}")
            return response

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error for {url}: {e}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None

    def close(self):
        """Close the HTTP session."""
        self.session.close()
        logger.debug("HTTP session closed")
