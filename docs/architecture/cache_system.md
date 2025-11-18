# File System Cache System

## Overview

The Deal Watcher system includes a comprehensive file system cache that stores all scraped listings locally. This enables offline analysis, filter development, and historical tracking without repeatedly downloading data from source websites.

## Why Use the Cache?

1. **Avoid Re-downloading**: All listings are saved locally, allowing you to test filters and analyze data without making repeated HTTP requests
2. **Historical Tracking**: Multiple versions of each listing are stored when content changes (especially price changes)
3. **Faster Development**: Test and tweak filters on cached data without waiting for scraping
4. **Bandwidth Efficient**: Reduces load on source websites
5. **Data Persistence**: Keep records even after listings are removed from source websites

## Cache Directory Structure

```
cache/
├── bazos/                  # Source website
│   ├── auto/              # Category
│   │   ├── 184779117/     # Listing ID
│   │   │   ├── 2025-11-15_143020.json
│   │   │   └── 2025-11-16_091234.json  # New version after price change
│   │   └── 184779118/
│   │       └── 2025-11-15_143025.json
│   └── reality/
│       ├── 183456789/
│       │   └── 2025-11-15_120000.json
│       └── 183456790/
│           ├── 2025-11-15_120005.json
│           └── 2025-11-15_153000.json  # Updated description
└── future_source/         # Future data sources
    └── ...
```

## Cache File Format

Each cached listing is stored as a JSON file with the following structure:

```json
{
  "cached_at": "2025-11-15T14:30:20.123456",
  "source": "bazos",
  "category": "auto",
  "listing_id": "184779117",
  "data": {
    "external_id": "184779117",
    "title": "BMW E46 330i Manual",
    "description": "Full description text...",
    "price": 12500.0,
    "location": "Bratislava",
    "postal_code": "821 01",
    "url": "https://auto.bazos.sk/inzerat/184779117/...",
    "view_count": 45,
    "image_url": "https://...",
    "images": ["https://...", "https://..."],
    "posted_date": "2025-11-10T00:00:00",
    "extra_data": {}
  }
}
```

## Filename Convention

Filenames use the format: `YYYY-MM-DD_HHMMSS.json`

Examples:
- `2025-11-15_143020.json` - Cached on Nov 15, 2025 at 14:30:20
- `2025-11-16_091234.json` - Updated version cached on Nov 16, 2025 at 09:12:34

This naming convention ensures:
- Chronological sorting (newest first when sorted in reverse)
- Easy identification of cache time
- No filename conflicts

## How It Works

### 1. During Scraping

```python
# All listings are saved to cache, regardless of filter match
for listing in scraped_listings:
    # Save basic info from list page
    cache_manager.save_listing(source, category, listing)

    # If passes quick filter, fetch details
    if quick_filter_matches:
        detail_data = scraper.scrape_detail_page(url)
        listing.update(detail_data)

        # Save detailed version (creates new file if changed)
        cache_manager.save_listing(source, category, listing)

        # If passes detailed filter, save to database
        if detailed_filter_matches:
            repository.save_to_database(listing)
```

### 2. Change Detection

When saving a listing that already exists in cache:

```python
change_info = cache_manager.detect_changes(source, category, listing_id, new_data)

if change_info['changed']:
    print(f"Changes detected: {change_info['differences']}")
    # Creates new cache file with current timestamp
```

Tracked fields for changes:
- `title`
- `description`
- `price`
- `location`

### 3. Retrieving from Cache

```python
# Get latest version
latest = cache_manager.get_latest_listing(source, category, listing_id)

# Get full history
history = cache_manager.get_listing_history(source, category, listing_id)

# Check if exists
exists = cache_manager.has_listing(source, category, listing_id)
```

## Configuration

Enable/disable the cache in `config.json`:

```json
{
  "cache": {
    "enabled": true,
    "cache_dir": "cache",
    "save_all_listings": true
  }
}
```

**Options:**
- `enabled`: Enable/disable file system caching (default: `true`)
- `cache_dir`: Root directory for cache storage (default: `"cache"`)
- `save_all_listings`: Save all scraped listings, not just matches (default: `true`)

## Scraper Configuration

Each scraper needs `source` and `category` fields:

```json
{
  "name": "BMW E-Series Manual",
  "source": "bazos",      # Data source identifier
  "category": "auto",     # Category within source
  "url": "https://auto.bazos.sk/bmw/",
  "type": "auto",
  ...
}
```

## Working with Cached Data

### View Cache Statistics

The system automatically displays cache stats at the end of each run:

```
Cache Statistics:
  - Total cached listings: 1,234
  - Total cache files: 2,456
  - bazos: 1,234 listings
```

### Manually Access Cache

```python
from deal_watcher.cache.cache_manager import CacheManager

cache = CacheManager('cache')

# Get all listing IDs for a category
listing_ids = cache.get_all_cached_listings('bazos', 'auto')

# Get latest version of a specific listing
listing = cache.get_latest_listing('bazos', 'auto', '184779117')

# Get price history
history = cache.get_listing_history('bazos', 'auto', '184779117')
for version in history:
    print(f"{version['cached_at']}: {version['data']['price']}€")

# Get cache statistics
stats = cache.get_cache_stats()
print(stats)
```

## Use Cases

### 1. Develop and Test Filters Offline

1. Run scraper once to populate cache
2. Disable scraping, work with cached data
3. Modify filters in `config.json`
4. Test filters on cached data without re-scraping

```python
# Run once to cache data
python -m deal_watcher.main

# Now work offline - filters can be tested on cached data
# Modify config.json filters as needed
```

### 2. Analyze Price Trends

```python
from deal_watcher.cache.cache_manager import CacheManager

cache = CacheManager('cache')
listing_ids = cache.get_all_cached_listings('bazos', 'auto')

for listing_id in listing_ids:
    history = cache.get_listing_history('bazos', 'auto', listing_id)

    if len(history) > 1:
        print(f"Listing {listing_id} has {len(history)} versions:")
        for version in history:
            price = version['data'].get('price')
            print(f"  {version['cached_at']}: {price}€")
```

### 3. Find Recently Changed Listings

```python
from datetime import datetime, timedelta

recent_cutoff = datetime.now() - timedelta(hours=24)

for listing_id in cache.get_all_cached_listings('bazos', 'auto'):
    history = cache.get_listing_history('bazos', 'auto', listing_id)

    if len(history) > 1:
        latest_time = datetime.fromisoformat(history[0]['cached_at'])
        if latest_time > recent_cutoff:
            print(f"Recently updated: {listing_id}")
```

## Storage Considerations

### Disk Space

- Each JSON file is typically 2-5 KB
- 10,000 listings ≈ 20-50 MB
- Multiple versions increase storage proportionally
- Images are NOT stored (only URLs)

### Performance

- Fast lookup by listing ID (directory-based)
- Chronological ordering via filename
- Minimal memory footprint
- Suitable for 100,000+ cached listings

## Best Practices

1. **Regular Scraping**: Run periodically to keep cache updated
2. **Monitor Disk Space**: Clean old versions if disk space is limited
3. **Backup Cache**: Consider backing up the cache directory for historical analysis
4. **Source Separation**: Keep different data sources in separate directories (already done automatically)

## Future Enhancements

Potential improvements to the cache system:

- Cache expiration/cleanup policies
- Compression for older cache files
- Database indexing of cache metadata
- Cache warmup from database
- Export cache to CSV/Excel for analysis
- Cache statistics dashboard

## Troubleshooting

### Cache Not Working

Check:
1. `cache.enabled` is `true` in config.json
2. Cache directory exists and is writable
3. Scrapers have `source` and `category` fields configured
4. Check logs for cache-related errors

### Disk Space Issues

```bash
# Check cache size
du -sh cache/

# Count cached listings
find cache/ -type d -mindepth 3 | wc -l

# Count total cache files
find cache/ -name "*.json" | wc -l
```

### Clean Old Cache Versions

```python
# Keep only latest version of each listing
from pathlib import Path
import json

cache_dir = Path('cache')
for listing_dir in cache_dir.rglob('*/*/*'):
    if listing_dir.is_dir():
        files = sorted(listing_dir.glob('*.json'), reverse=True)
        # Keep first (newest), delete rest
        for old_file in files[1:]:
            old_file.unlink()
            print(f"Deleted old version: {old_file}")
```
