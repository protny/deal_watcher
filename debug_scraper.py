"""Debug script to test scraping with actual dependencies."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deal_watcher.utils.http_client import HTTPClient
from deal_watcher.utils.logger import setup_logger
from bs4 import BeautifulSoup

logger = setup_logger('debug', level='DEBUG')

def debug_bazos_html():
    """Fetch Bazos.sk and analyze HTML structure."""

    http_client = HTTPClient(timeout=30, request_delay=0)

    url = "https://auto.bazos.sk/bmw/"
    logger.info(f"Fetching: {url}")

    response = http_client.get(url, skip_rate_limit=True)

    if not response:
        logger.error("Failed to fetch page")
        return

    logger.info(f"Got response: {response.status_code}")
    logger.info(f"Content length: {len(response.content)} bytes")

    soup = BeautifulSoup(response.content, 'lxml')

    # Save full HTML
    with open('/tmp/bazos_full.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    logger.info("Saved full HTML to /tmp/bazos_full.html")

    # Look for different patterns
    logger.info("\n=== Analyzing structure ===")

    # Check for tables (common in older Slovak sites)
    tables = soup.find_all('table')
    logger.info(f"Found {len(tables)} tables")

    # Check for common div classes
    for class_name in ['inzerat', 'inzeraty', 'inzeratycena', 'nadpis', 'popis']:
        divs = soup.find_all(attrs={'class': class_name})
        logger.info(f"Found {len(divs)} elements with class='{class_name}'")

    # Look for links to /inzerat/
    all_links = soup.find_all('a', href=True)
    inzerat_links = [a for a in all_links if '/inzerat/' in a.get('href', '')]
    logger.info(f"\nFound {len(inzerat_links)} links to /inzerat/")

    if inzerat_links:
        logger.info("\nFirst 3 listing links:")
        for i, link in enumerate(inzerat_links[:3]):
            logger.info(f"\n  Link {i+1}:")
            logger.info(f"    href: {link.get('href')}")
            logger.info(f"    text: {link.get_text(strip=True)[:60]}")
            logger.info(f"    classes: {link.get('class')}")

            # Check parent
            parent = link.parent
            logger.info(f"    parent: <{parent.name}> with classes: {parent.get('class')}")

            # Check for nearby price/location
            if parent:
                siblings = list(parent.next_siblings)
                logger.info(f"    parent has {len(siblings)} next siblings")

    http_client.close()

if __name__ == '__main__':
    debug_bazos_html()
