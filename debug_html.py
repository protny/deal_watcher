"""Debug script to inspect Bazos.sk HTML structure."""

import requests
from bs4 import BeautifulSoup

def inspect_bazos():
    """Fetch and inspect Bazos.sk page structure."""
    url = "https://auto.bazos.sk/bmw/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")

    soup = BeautifulSoup(response.content, 'lxml')

    # Look for different possible listing containers
    print("\n=== Searching for listing containers ===")

    # Try common patterns
    patterns = [
        ('div', {'class': 'inzerat'}),
        ('div', {'class': 'inzeraty'}),
        ('div', {'class': 'inzeratycena'}),
        ('table', {}),
        ('tr', {}),
    ]

    for tag, attrs in patterns:
        elements = soup.find_all(tag, attrs)
        if elements:
            print(f"\nFound {len(elements)} <{tag}> elements with {attrs}")
            if len(elements) > 0:
                print("First element HTML (truncated to 500 chars):")
                print(str(elements[0])[:500])

    # Look for links to listings
    print("\n=== Looking for listing links ===")
    links = soup.find_all('a', href=True)
    inzerat_links = [a for a in links if '/inzerat/' in a.get('href', '')]
    print(f"Found {len(inzerat_links)} links to /inzerat/")

    if inzerat_links:
        print("\nFirst listing link:")
        print(f"  href: {inzerat_links[0].get('href')}")
        print(f"  text: {inzerat_links[0].get_text(strip=True)[:100]}")
        print(f"  Full HTML: {str(inzerat_links[0])[:300]}")

        # Check parent structure
        parent = inzerat_links[0].parent
        print(f"\nParent tag: {parent.name}")
        print(f"Parent classes: {parent.get('class')}")
        print(f"Parent HTML (truncated): {str(parent)[:500]}")

    # Save full HTML for inspection
    with open('/tmp/bazos_debug.html', 'w', encoding='utf-8') as f:
        f.write(soup.prettify())
    print("\n\nFull HTML saved to /tmp/bazos_debug.html")

if __name__ == '__main__':
    inspect_bazos()
