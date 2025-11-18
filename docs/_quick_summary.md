# Quick Reference Guide

## Executable Scripts

### Main Scripts (Production Use)

#### `downloader.py`
**Purpose**: Downloads raw HTML pages from configured websites and caches them locally.

**Usage**:
```bash
python downloader.py
```

**Configuration**: `download_config.json`
- Specify URLs to download
- Set max pages per category
- Configure request delays and timeouts

**Output**: HTML files in `cache/bazos/{category}/page_*.html`

---

#### `processor.py`
**Purpose**: Processes cached HTML pages, extracts listings, applies filters, and saves matches to PostgreSQL database.

**Usage**:
```bash
python processor.py
```

**Configuration**: `deal_watcher/config/config.json`
- Define filter criteria
- Set scraping mode ("new" or "full")
- Configure category mappings

**Requirements**: PostgreSQL database must be set up and `.env` file configured.

---

### Test & Debug Scripts

#### `test_filters.py`
**Purpose**: Validates that BMW and Reality filters work correctly with 12 comprehensive test cases.

**Usage**:
```bash
python test_filters.py
```

**Expected Output**:
- BMW Filter: 6/6 tests passed
- Reality Filter: 6/6 tests passed
- Total: 12 test cases

**When to use**: Before deploying changes to filters, after modifying filter logic.

---

#### `test_scraper.py`
**Purpose**: Tests scraping functionality without database. Validates HTML parsing and filter logic.

**Usage**:
```bash
python test_scraper.py
```

**What it tests**:
- HTML parsing for Bazos.sk
- Listing extraction
- Filter matching
- Area extraction and conversion

---

#### `debug_scraper.py`
**Purpose**: Interactive debugging of scraper logic. Allows testing specific URLs and seeing detailed extraction output.

**Usage**:
```bash
python debug_scraper.py
```

**Features**:
- Test specific URLs
- See raw HTML parsing results
- Debug filter decisions
- Inspect extracted data

---

#### `debug_html.py`
**Purpose**: Inspects HTML structure of cached or live pages to debug parsing issues.

**Usage**:
```bash
python debug_html.py
```

**Use cases**:
- Website structure changed
- Parsing not working correctly
- Need to verify HTML selectors

---

#### `test_imports.py`
**Purpose**: Verifies all Python dependencies are installed correctly.

**Usage**:
```bash
python test_imports.py
```

**Checks**:
- Required packages (requests, beautifulsoup4, sqlalchemy, psycopg2, etc.)
- Module imports
- Package versions

---

### Setup & Utility Scripts

#### `validate_setup.py`
**Purpose**: Comprehensive validation of environment setup.

**Usage**:
```bash
python validate_setup.py
```

**Validates**:
- Python version (3.10+)
- Required packages installed
- Configuration files exist
- Database connection works
- `.env` file configured

---

#### `run_migration.py`
**Purpose**: Runs database migration to rename `metadata` column to `extra_data`.

**Usage**:
```bash
python run_migration.py
```

**Required**: Must be run once before using the system (if upgrading from old version).

**What it does**:
- Renames `deals.metadata` → `deals.extra_data`
- Updates database indexes
- Validates migration success

---

#### `quick_setup.sh`
**Purpose**: Automated setup script for initial installation (Bash script).

**Usage**:
```bash
chmod +x quick_setup.sh
./quick_setup.sh
```

**Steps**:
- Creates virtual environment
- Installs dependencies
- Sets up database
- Configures environment

---

### Legacy Script (Deprecated)

#### `deal_watcher/main.py`
**Purpose**: Old combined scraper (before two-stage architecture).

**Status**: Deprecated, use `downloader.py` + `processor.py` instead.

---

## Configuration Files

### `download_config.json`
Controls downloader behavior. Specifies which URLs to scrape and how many pages.

**Key sections**:
- `download_settings`: Request delays, timeouts, user agents
- `urls_to_download`: List of URLs with max pages and cache subdirectories

---

### `deal_watcher/config/config.json`
Controls processor behavior. Defines filters and scraping modes.

**Key sections**:
- `scrapers`: Scraper configurations with filters
- `scraping`: Request settings
- `cache`: Cache configuration
- `mode`: "new" (7 days) or "full" (all pages)

---

### `.env`
Environment variables for database and logging.

**Required variables**:
- `DB_CONNECTION_STRING`: PostgreSQL connection string
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

**Example**:
```
DB_CONNECTION_STRING=postgresql://postgres:password@localhost:5432/deal_watcher
LOG_LEVEL=INFO
```

---

### `.env.example`
Template for `.env` file. Copy to `.env` and configure.

---

## Documentation Files

### Root Documentation

#### `README.md` (in project root)
Main project overview and getting started guide.

**Contents**:
- Project description and features
- Installation instructions
- Usage examples
- Configuration guide
- Troubleshooting

**Audience**: New users, general overview

---

### `docs/setup/`

#### `setup_guide.md`
Detailed setup instructions and troubleshooting.

**Contents**:
- Fixed issues and solutions
- Database setup steps
- Environment configuration
- Test results
- Troubleshooting common problems

**Audience**: First-time setup, installation issues

---

### `docs/architecture/`

#### `design_document.md`
System architecture and technical design decisions.

**Contents**:
- Website data format analysis
- Data extraction mechanism
- Database schema design
- Filtering system architecture
- Execution flow
- Recommendations and next steps

**Audience**: Developers, contributors, architecture review

---

#### `cache_system.md`
File system cache system documentation.

**Contents**:
- Why use cache
- Cache directory structure
- Cache file format
- Change detection logic
- Configuration options
- Use cases and examples
- Troubleshooting

**Audience**: Understanding cache system, offline development

---

#### `workflow.md`
Two-stage workflow documentation (downloader + processor).

**Contents**:
- Downloader explanation
- Processor explanation
- Complete workflow steps
- Regular update procedures
- Advantages of separation
- Directory structure

**Audience**: Understanding system workflow, deployment

---

### `docs/development/`

#### `implementation_summary.md`
Detailed summary of completed features and improvements.

**Contents**:
- Bug fixes (accent normalization, area extraction, price validation)
- Performance optimizations
- Filter enhancements
- Testing and validation
- Database migration
- Performance metrics
- Troubleshooting

**Audience**: Developers, understanding what was implemented

---

#### `original_requirements.md`
Original project requirements and specification.

**Contents**:
- Initial project goals
- Target websites and categories
- Search criteria
- Storage requirements
- Configuration approach

**Audience**: Historical context, project origins

---

### `docs/`

#### `_work.md`
Comprehensive work summary and future development plans.

**Contents**:
- What has been completed
- Current system status
- Known issues and limitations
- Future development needs (high/medium/low priority)
- Suggested next steps
- Deployment checklist
- Maintenance tasks

**Audience**: Project management, planning, resuming work after break

---

#### `_quick_summary.md` (this file)
Quick reference for all scripts and documentation.

**Contents**:
- All executable scripts with usage
- All configuration files
- All documentation files with summaries

**Audience**: Quick lookup, finding the right tool or document

---

## Database Files

### `database/schema.sql`
PostgreSQL database schema definition.

**Contains**:
- Table definitions (categories, deals, price_history, deal_images, scraping_runs)
- Indexes
- Constraints
- Sample data inserts

**Usage**: Initialize database
```bash
psql -d deal_watcher -f database/schema.sql
```

---

## Common Workflows

### Initial Setup
1. Run `python validate_setup.py` to check prerequisites
2. Edit `.env` with database connection
3. Run `python run_migration.py` (if upgrading)
4. Test: `python test_filters.py` and `python test_scraper.py`

### Daily Scraping (Production)
1. Run `python downloader.py` to fetch new pages
2. Run `python processor.py` to process and save matches
3. Check logs for errors
4. Query database for new matches

### Filter Development
1. Run `python downloader.py` once to cache pages
2. Modify filters in `deal_watcher/config/config.json`
3. Run `python test_filters.py` to validate
4. Run `python processor.py` to test on cached data
5. Repeat steps 2-4 until satisfied

### Debugging Issues
1. Check logs (console output or log files)
2. Run `python validate_setup.py` for environment issues
3. Run `python test_filters.py` for filter issues
4. Run `python test_scraper.py` for scraping issues
5. Use `python debug_scraper.py` or `python debug_html.py` for detailed inspection

---

## Quick Command Reference

```bash
# Setup
python validate_setup.py          # Validate environment
python run_migration.py           # Run database migration
python test_imports.py            # Check dependencies

# Testing
python test_filters.py            # Test filter logic
python test_scraper.py            # Test scraping without DB

# Production
python downloader.py              # Download fresh pages
python processor.py               # Process and save to DB

# Debugging
python debug_scraper.py           # Interactive scraper debugging
python debug_html.py              # Inspect HTML structure

# Database
psql -d deal_watcher -f database/schema.sql  # Initialize DB
psql -d deal_watcher              # Open database shell
```

---

## File & Directory Structure

```
deal_watcher/
├── README.md                      # Main project overview
├── .env                           # Environment variables (create from .env.example)
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
├── download_config.json           # Downloader configuration
│
├── downloader.py                  # Main: Download HTML pages
├── processor.py                   # Main: Process cached pages
│
├── test_filters.py                # Test: Validate filters
├── test_scraper.py                # Test: Validate scraping
├── test_imports.py                # Test: Check dependencies
├── validate_setup.py              # Utility: Environment validation
├── run_migration.py               # Utility: Database migration
├── debug_scraper.py               # Debug: Scraper debugging
├── debug_html.py                  # Debug: HTML inspection
├── quick_setup.sh                 # Setup: Automated setup script
│
├── docs/                          # Documentation root
│   ├── _work.md                   # Work summary & future plans
│   ├── _quick_summary.md          # This file - quick reference
│   ├── setup/
│   │   └── setup_guide.md         # Setup & troubleshooting
│   ├── architecture/
│   │   ├── design_document.md     # System architecture
│   │   ├── cache_system.md        # Cache system docs
│   │   └── workflow.md            # Two-stage workflow
│   └── development/
│       ├── implementation_summary.md  # Completed features
│       └── original_requirements.md   # Original project spec
│
├── database/
│   └── schema.sql                 # PostgreSQL schema
│
├── deal_watcher/                  # Main Python package
│   ├── config/
│   │   └── config.json            # Processor configuration
│   ├── scrapers/                  # Scraper modules
│   ├── filters/                   # Filter modules
│   ├── database/                  # Database models
│   ├── cache/                     # Cache manager
│   ├── utils/                     # Utilities
│   └── main.py                    # Legacy: Old combined scraper
│
└── cache/                         # Cached HTML pages (gitignored)
    └── bazos/
        ├── auto-bmw/
        ├── reality-pozemok/
        ├── reality-dom/
        └── reality-chata/
```

---

## Need Help?

1. **Getting Started**: Read `README.md` in project root
2. **Setup Issues**: Check `docs/setup/setup_guide.md`
3. **Understanding Architecture**: Read `docs/architecture/design_document.md`
4. **Filter Problems**: Read `docs/development/implementation_summary.md`
5. **Planning Next Steps**: Read `docs/_work.md`
6. **Quick Lookup**: This file (`docs/_quick_summary.md`)

---

**Last Updated**: 2025-11-18
