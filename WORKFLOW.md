# Deal Watcher - Two-Stage Workflow

The system is split into two separate scripts for maximum flexibility:

## 1. Downloader (downloader.py)

Downloads raw HTML pages and stores them in the cache directory.

### Configuration: `download_config.json`

```json
{
  "download_settings": {
    "request_delay_seconds": 2.5,
    "timeout_seconds": 30,
    ...
  },
  "urls_to_download": [
    {
      "name": "BMW Auto Listings",
      "base_url": "https://auto.bazos.sk/bmw/",
      "max_pages": 100,
      "cache_subdir": "auto-bmw"
    }
  ]
}
```

### Usage

```bash
python downloader.py
```

### What it does

- Fetches HTML pages from configured URLs
- Stores them in `cache/bazos/{cache_subdir}/page_0001.html`, etc.
- Saves metadata (URL, timestamp, size) in `.meta.json` files
- No filtering, no processing - just downloads and caches

### Output

```
cache/bazos/
├── auto-bmw/
│   ├── page_0000.html
│   ├── page_0000.meta.json
│   ├── page_0001.html
│   ├── page_0001.meta.json
│   └── ...
├── reality-pozemok/
│   └── ...
└── reality-dom/
    └── ...
```

## 2. Processor (processor.py)

Reads cached HTML pages, extracts listings, applies filters, saves to database.

### Configuration: `deal_watcher/config/config.json`

Uses the same config file with scraper and filter definitions.

### Usage

```bash
python processor.py
```

### What it does

- Reads HTML pages from `cache/bazos/`
- Extracts all listings using scraper parsing logic
- Fetches detail pages for all listings (live HTTP request)
- Applies configured filters
- Saves matches to PostgreSQL database

### Benefits

- Process cached data offline (no re-downloading list pages)
- Tweak filters and re-run processor without bandwidth usage
- Complete separation of download and processing logic

## Complete Workflow

### Initial Setup

1. **Configure downloads**
   ```bash
   # Edit download_config.json
   # Add URLs you want to scrape
   ```

2. **Download pages**
   ```bash
   python downloader.py
   ```
   This builds your local cache of all listing pages.

3. **Configure filters**
   ```bash
   # Edit deal_watcher/config/config.json
   # Set your filter criteria
   ```

4. **Process cached data**
   ```bash
   python processor.py
   ```
   This extracts listings, applies filters, saves to DB.

### Regular Updates

**Option A: Download new pages, then process**
```bash
# Update cache (downloads only new/changed pages)
python downloader.py

# Process the updated cache
python processor.py
```

**Option B: Just reprocess with new filters**
```bash
# Modify filters in config.json
# Then reprocess cached data
python processor.py
```

### Scheduled Execution

```bash
# crontab -e

# Download fresh data every 6 hours
0 */6 * * * cd /path/to/deal_watcher && python downloader.py

# Process data 30 minutes after download
30 */6 * * * cd /path/to/deal_watcher && python processor.py
```

## Directory Structure

```
deal_watcher/
├── downloader.py              # Stage 1: Download HTML pages
├── processor.py               # Stage 2: Extract, filter, save to DB
├── download_config.json       # Config for downloader
├── deal_watcher/
│   └── config/
│       └── config.json        # Config for processor (filters, etc.)
└── cache/
    └── bazos/
        ├── auto-bmw/         # Cached HTML pages
        ├── reality-pozemok/
        ├── reality-dom/
        └── reality-chata/
```

## Advantages of This Approach

1. **Separation of Concerns**
   - Download logic completely separate from processing
   - Easy to maintain and debug

2. **Bandwidth Efficiency**
   - Download pages once
   - Process multiple times with different filters
   - No re-downloading for filter changes

3. **Faster Iteration**
   - Test filters on cached data instantly
   - No waiting for scraping between tests

4. **Flexibility**
   - Download and process on different schedules
   - Download on one machine, process on another
   - Archive downloaded pages for historical analysis

5. **Resilience**
   - If processing fails, cache is still intact
   - Can reprocess at any time without re-downloading

## Migration from Old System

The old `main.py` combined downloading and processing. To migrate:

1. Run `downloader.py` to build initial cache
2. Run `processor.py` to process cached data
3. Set up cron jobs for both scripts
4. Old cache manager (JSON listings) can be removed

The new system caches raw HTML instead of parsed JSON, giving you complete control over parsing and filtering logic.
