# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deal Watcher is a marketplace scraping system that monitors online classifieds (currently Bazos.sk) for BMW cars and large real estate plots. It uses a two-stage architecture: downloading HTML pages, then processing them with filters to identify matches.

## Commands

### Development Commands

```bash
# Run tests
python test_filters.py        # Validate filter logic (12 test cases)
python test_scraper.py         # Test scraper functionality

# Database operations
python run_migration.py        # Run database migrations
psql -d deal_watcher -f database/schema.sql         # Initialize schema
psql -d deal_watcher -f database/reset_schema.sql   # Reset database
```

### Two-Stage Workflow

```bash
# Stage 1: Download HTML pages (list pages and detail pages)
python downloader.py

# Stage 2: Process cached HTML, apply filters, save to database
python processor.py
```

### Legacy Single-Stage (deprecated)

```bash
# Old unified approach (still functional)
python -m deal_watcher.main
```

### Testing Individual Components

```bash
# Debug HTML parsing
python debug_html.py

# Debug scraper logic
python debug_scraper.py

# Validate environment setup
python validate_setup.py
```

### Database Queries

```bash
# Check new deals today
psql -d deal_watcher -c "SELECT COUNT(*) FROM deals WHERE first_seen_at::date = CURRENT_DATE;"

# View recent matches
psql -d deal_watcher -c "SELECT external_id, title, current_price FROM deals ORDER BY first_seen_at DESC LIMIT 10;"

# Check price changes
psql -d deal_watcher -c "SELECT COUNT(DISTINCT deal_id) FROM price_history WHERE changed_at > NOW() - INTERVAL '7 days';"
```

## Architecture

### Two-Stage Design

The system separates downloading from processing for flexibility and efficiency:

**Stage 1: Downloader (downloader.py)**
- Fetches raw HTML from Bazos.sk list pages
- Extracts individual listing URLs
- Downloads detail pages for each listing
- Caches everything as HTML files in `cache/bazos/{category}/`
- Configuration: `download_config.json`

**Stage 2: Processor (processor.py)**
- Reads cached HTML files
- Parses listings using BeautifulSoup
- Applies two-stage filtering (quick filter on list data, full filter on detail data)
- Saves matches to PostgreSQL database
- Configuration: `deal_watcher/config/config.json`

This separation allows:
- Offline filter development without re-scraping
- Different schedules for downloading vs processing
- Bandwidth efficiency when testing filters

### Core Components

**Scrapers** (`deal_watcher/scrapers/`)
- `base_scraper.py`: Abstract base with common scraping logic
- `bazos_scraper.py`: Bazos.sk-specific parsing (URL patterns, date extraction)
- `auto_scraper.py`: BMW vehicle scraper (extends BazosScraper)
- `reality_scraper.py`: Real estate scraper (extends BazosScraper)

**Filters** (`deal_watcher/filters/`)
- `base_filter.py`: Abstract base with Unicode normalization for Slovak accents
- `auto_filter.py`: BMW filtering (model codes, engine codes, transmission, fuel)
- `reality_filter.py`: Real estate filtering (area extraction with ha↔m² conversion, price validation)

**Cache System** (`deal_watcher/cache/`)
- `cache_manager.py`: File system cache for individual listing JSON files
- Stores versioned snapshots when listings change (especially price changes)
- Enables offline analysis and historical tracking
- Structure: `cache/{source}/{category}/{listing_id}/YYYY-MM-DD_HHMMSS.json`

**Database** (`deal_watcher/database/`)
- `models.py`: SQLAlchemy ORM models (Deal, Category, PriceHistory, etc.)
- `repository.py`: Database operations (CRUD, change detection, statistics)
- PostgreSQL schema with JSONB for flexible metadata storage

### Scraping Modes

Configured per scraper in `config.json`:

- **"new" mode** (default): Only processes listings from last N days (configurable via `days_back`), stops when hitting old listings. Ideal for daily cron jobs.
- **"full" mode**: Scrapes all pages up to `max_pages`. Use for initial data collection or full refresh.

### Filter Architecture

**Two-Stage Filtering:**

1. **Quick Filter** (on list page data):
   - Title + price only
   - Fast rejection of obvious non-matches
   - Reduces detail page fetches by 80-90%

2. **Full Filter** (on detail page data):
   - Complete description analysis
   - Complex logic (area extraction, engine code detection)
   - Only runs if quick filter passes

**Slovak Text Normalization:**

All filters inherit Unicode normalization from `BaseFilter`:
- Removes Slovak accents: á→a, č→c, ď→d, é→e, í→i, ľ→l, ň→n, ó→o, ŕ→r, š→s, ť→t, ú→u, ý→y, ž→z
- Enables "benzin" to match "benzín", "manual" to match "manuál"
- Critical for reliable keyword matching in Slovak text

### Reality Filter Area Detection

Complex logic to distinguish land area from floor area:

1. Extracts all numbers with area units (m², ha, hektár, etc.)
2. Captures 60 characters of context before/after each number
3. Classifies as "land" or "floor" based on keywords:
   - **Land keywords**: pozemok, parcela, pozemku, parcely, ha, hektár
   - **Floor keywords**: podlahová plocha, úžitková plocha, zastavená plocha
4. Returns largest land area found
5. Falls back to largest area if >5000 m² (likely land)
6. Converts hectares to m² (1 ha = 10,000 m²)

**Price Validation:**
- Rejects prices with per-m² indicators: `/m²`, `€/m2`, `za m²`
- Rejects suspiciously low prices (<100 EUR) as likely per-m²
- Controlled by `reject_price_per_m2: true` (default)

## Configuration Files

**deal_watcher/config/config.json**
- Scraper definitions (URL, category, filters)
- Filter criteria (keywords, price ranges, area thresholds)
- Scraping behavior (request delays, retries, user agents)
- Database connection (uses `${DB_CONNECTION_STRING}` from .env)
- Cache settings

**download_config.json**
- URLs to download (base_url, max_pages, cache_subdir)
- Download settings (delays, timeout, user agent)
- Used by `downloader.py` only

**.env**
- `DB_CONNECTION_STRING`: PostgreSQL connection (postgresql://user:pass@host:port/db)
- `LOG_LEVEL`: INFO (production) or DEBUG (development)

## Database Schema

**Key Tables:**

- `categories`: Scraper categories (auto, reality subcategories)
- `deals`: Main listings table with JSONB `extra_data` column for flexible metadata
- `price_history`: Price change tracking (deal_id, price, changed_at)
- `deal_images`: Image URLs for listings
- `scraping_runs`: Execution history and statistics

**Important:** The code uses `extra_data` column but older databases may have `metadata`. Run `python run_migration.py` to rename the column.

## Development Workflow

### Adding New Filters

1. Modify filter configuration in `deal_watcher/config/config.json`
2. Test with cached data: `python processor.py` (no re-downloading)
3. Validate with test suite: `python test_filters.py`
4. Check matches in database with SQL queries

### Adding New Scrapers

1. Create scraper class inheriting from `BazosScraper` or `BaseScraper`
2. Implement required abstract methods (if any)
3. Create corresponding filter class inheriting from `BaseFilter`
4. Add scraper configuration to `config.json`
5. Add URL to `download_config.json`
6. Create database category: `INSERT INTO categories ...`

### Testing Filter Changes

Since filters operate on cached data, you can iterate quickly:

```bash
# 1. Download fresh data once
python downloader.py

# 2. Edit filters in config.json
# 3. Reprocess cached data (instant)
python processor.py

# 4. Check results
psql -d deal_watcher -c "SELECT * FROM deals WHERE first_seen_at > NOW() - INTERVAL '1 hour';"

# 5. Repeat steps 2-4 until satisfied
```

### Running in Production

```bash
# Setup cron jobs for automated execution
crontab -e

# Download fresh data every 6 hours
0 */6 * * * cd /path/to/deal_watcher && python downloader.py >> /var/log/deal_watcher_download.log 2>&1

# Process data 30 minutes after download
30 */6 * * * cd /path/to/deal_watcher && python processor.py >> /var/log/deal_watcher_process.log 2>&1
```

## Known Issues and Gotchas

**Database Column Mismatch:**
- Code expects `extra_data` column in deals table
- Older installations may have `metadata` column
- Fix: Run `python run_migration.py` before first use

**Slovak Accent Sensitivity:**
- Always use normalized text for keyword matching
- Filters inherit normalization from `BaseFilter.normalize_text()`
- Never compare raw Slovak text without normalization

**Area Detection Edge Cases:**
- Real estate listings often include BOTH floor area and land area
- Filter prioritizes land area by detecting context keywords
- If both are labeled as land, it picks the largest
- Test with: `python test_filters.py` (includes area detection tests)

**Price per m² False Positives:**
- Some listings show price per m² instead of total price
- Filter rejects prices <100 EUR and prices with /m² indicators
- Controlled by `reject_price_per_m2: true` in filter config

**Caching Behavior:**
- Downloader creates MD5-hashed filenames for list pages
- Detail pages cached by listing ID
- Cache never expires automatically (manual cleanup required)
- To force refresh: delete cache directory and re-run downloader

## File Locations

**Source Code:**
- Main application: `deal_watcher/`
- Stage 1 script: `downloader.py`
- Stage 2 script: `processor.py`
- Tests: `test_*.py` files in root

**Configuration:**
- Application config: `deal_watcher/config/config.json`
- Download config: `download_config.json`
- Environment: `.env` (create from `.env.example`)

**Database:**
- Schema: `database/schema.sql`
- Migrations: `database/migrations/*.sql`
- Reset script: `database/reset_schema.sql`

**Cache:**
- HTML pages: `cache/bazos/{category}/` (created by downloader)
- Listing JSON: `cache/{source}/{category}/{listing_id}/` (created by old cache manager)

**Documentation:**
- Workflow guide: `WORKFLOW.md`
- Cache system: `CACHE_SYSTEM.md`
- Implementation notes: `IMPLEMENTATION_SUMMARY.md`
- Setup guide: `SETUP_NOTES.md`
