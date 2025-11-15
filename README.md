# Deal Watcher

A modular system that tracks deals from online marketplaces. It periodically checks for new deals and monitors changes like price drops in existing listings.

## Features

- **Modular Scraping**: Extensible scrapers for different websites
- **Smart Filtering**: Configurable filters for specific criteria
- **Price Tracking**: Monitors price changes over time
- **PostgreSQL Storage**: Robust data storage with history tracking
- **File System Cache**: All listings cached locally for offline analysis and filter development
- **Change Detection**: Automatic versioning when listings are modified
- **Automated Execution**: Designed for periodic execution via cron

## Current Implementations

### Supported Sites

1. **Auto Listings (Bazos.sk)**
   - BMW E36, E46, E39 vehicles
   - Filters: 6-cylinder petrol engine, manual transmission

2. **Real Estate (Bazos.sk)**
   - Land plots, houses, and cottages
   - Filters: ≥40,000 m² (4 hectares), price <400,000 EUR

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone the repository**

```bash
cd deal_watcher
```

2. **Create virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database**

```bash
# Create database
createdb deal_watcher

# Or using psql:
psql -U postgres
CREATE DATABASE deal_watcher;
\q
```

5. **Initialize database schema**

```bash
psql -U postgres -d deal_watcher -f database/schema.sql
```

6. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env and set your database connection string
```

Example `.env` file:
```
DB_CONNECTION_STRING=postgresql://username:password@localhost:5432/deal_watcher
LOG_LEVEL=INFO
```

7. **Customize configuration** (optional)

Edit `deal_watcher/config/config.json` to customize:
- Search criteria
- Max pages to scrape
- Request delays
- Filter parameters

## Usage

### Run the scraper

```bash
python -m deal_watcher.main
```

### Output Example

```
[2025-11-12 10:30:15] INFO - Starting scraper: BMW E-Series Manual
[2025-11-12 10:30:18] INFO - Scraping page 1/10
[2025-11-12 10:30:18] INFO - Found 20 listings on page 1
[2025-11-12 10:30:45] INFO - ✓ NEW: BMW E46 330i Manual - 12,500€ (ID: 184779117)
[2025-11-12 10:31:02] INFO - ↓ PRICE CHANGE: BMW E39 528i - 8,200€ (ID: 183456789)
[2025-11-12 10:45:30] INFO - Scraper complete: 15 new deals, 3 price changes
```

### Schedule with Cron

Add to crontab (`crontab -e`):

```bash
# Run every 6 hours
0 */6 * * * cd /path/to/deal_watcher && /path/to/venv/bin/python -m deal_watcher.main >> /var/log/deal_watcher.log 2>&1
```

## Project Structure

```
deal_watcher/
├── deal_watcher/
│   ├── config/
│   │   └── config.json           # Configuration file
│   ├── database/
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── repository.py          # Database operations
│   │   ├── schema.sql             # Database schema
│   │   └── migrations/            # Database migrations
│   ├── cache/
│   │   ├── cache_manager.py       # File system cache manager
│   │   └── __init__.py
│   ├── scrapers/
│   │   ├── base_scraper.py        # Abstract base scraper
│   │   ├── bazos_scraper.py       # Bazos.sk common logic
│   │   ├── auto_scraper.py        # Auto listings scraper
│   │   └── reality_scraper.py     # Real estate scraper
│   ├── filters/
│   │   ├── base_filter.py         # Abstract base filter
│   │   ├── auto_filter.py         # Auto listings filter
│   │   └── reality_filter.py      # Real estate filter
│   ├── utils/
│   │   ├── logger.py              # Logging utilities
│   │   └── http_client.py         # HTTP client with retries
│   └── main.py                    # Main CLI application
├── cache/                         # File system cache (gitignored)
│   └── bazos/                     # Organized by source
│       ├── auto/                  # And category
│       └── reality/
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── README.md                      # This file
├── CACHE_SYSTEM.md               # Cache system documentation
└── DESIGN_DOCUMENT.md            # System design documentation
```

## Database Schema

### Tables

- **categories**: Scraping categories (auto, reality)
- **deals**: Main deals table
- **price_history**: Price change tracking
- **deal_images**: Deal images
- **scraping_runs**: Execution history and statistics

### Key Features

- Price history tracking
- Deal lifecycle tracking (first seen, last seen, active status)
- Flexible metadata storage (JSONB)
- Comprehensive indexing for performance

## Configuration

### Scraper Configuration

Edit `deal_watcher/config/config.json`:

```json
{
  "scrapers": [
    {
      "name": "BMW E-Series Manual",
      "enabled": true,
      "category_id": 1,
      "url": "https://auto.bazos.sk/bmw/",
      "type": "auto",
      "max_pages": 10,
      "filters": {
        "keywords_any": ["E36", "E46", "E39"],
        "keywords_all": ["benzin", "manuál"],
        "keywords_engine": ["6 valec", "6-valec"],
        "keywords_excluded": ["havarovan", "automat"]
      }
    }
  ]
}
```

### Filter Types

**Auto Filter**:
- `keywords_any`: At least one must match (models)
- `keywords_all`: All must be present (fuel, transmission)
- `keywords_engine`: At least one engine type must match
- `keywords_excluded`: None should be present
- `price_min`, `price_max`: Price range

**Reality Filter**:
- `area_min`: Minimum area in m²
- `price_max`: Maximum price
- `keywords_excluded`: Exclude specific terms

## Development

### Adding New Scrapers

1. Create scraper class inheriting from `BaseScraper`
2. Implement required abstract methods
3. Add configuration to `config.json`
4. Create corresponding filter class

### Adding New Filters

1. Create filter class inheriting from `BaseFilter`
2. Implement `matches()` method
3. Add filter factory logic in `main.py`

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U username -d deal_watcher -c "SELECT 1;"
```

### Import Errors

```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Scraping Failures

- Check `LOG_LEVEL=DEBUG` in `.env` for detailed logs
- Verify website structure hasn't changed
- Check network connectivity
- Review rate limiting settings

## Legal & Ethics

- This tool is for personal use only
- Respect website Terms of Service
- Implement appropriate rate limiting
- Do not republish scraped content
- Review robots.txt compliance

## File System Cache

All scraped listings are automatically cached to the file system, enabling:

- **Offline Analysis**: Test filters without re-scraping
- **Historical Tracking**: Multiple versions saved when content changes
- **Fast Iteration**: Develop filters on cached data
- **Data Persistence**: Keep records even after listings are removed

See [CACHE_SYSTEM.md](CACHE_SYSTEM.md) for detailed documentation.

### Cache Structure

```
cache/bazos/auto/184779117/
├── 2025-11-15_143020.json    # Initial scrape
└── 2025-11-16_091234.json    # After price change
```

### Cache Configuration

```json
{
  "cache": {
    "enabled": true,
    "cache_dir": "cache",
    "save_all_listings": true
  }
}
```

## Future Enhancements

- Email/Telegram notifications for new matches
- Web dashboard for browsing deals
- More sophisticated NLP filtering
- Additional website modules
- Cache analytics and visualization
- Deal similarity detection
- Market analytics and trends

## License

This project is for educational and personal use only.

## Support

For issues, questions, or contributions, please refer to the project documentation in `DESIGN_DOCUMENT.md`.
