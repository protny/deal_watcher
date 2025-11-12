# Deal Watcher - System Design Document

## 1. Website Data Format Analysis

### Bazos.sk Structure
Both auto.bazos.sk and reality.bazos.sk follow the same listing format:

**Common Fields:**
- **Listing ID**: Unique numeric identifier in URL (`/inzerat/{ID}/`)
- **Title**: Descriptive headline
- **Price**: EUR amount (some marked "Dohodou" for negotiable, "V texte" for in-description)
- **Location**: City name + postal code
- **Date Posted**: Format `[DD.MM. YYYY]`
- **View Count**: Number of views
- **Description**: Text excerpt on list page, full text on detail page
- **Images**: Thumbnail on list, multiple on detail page
- **Status**: "TOP" badge for promoted listings

**Pagination**: 20 listings per page, URL pattern `/category/{offset}/` (0, 20, 40...)

**Total Listings** (as of research):
- BMW category: ~8,152 listings
- Land (pozemok): ~12,884 listings
- Houses (dom): ~14,813 listings

## 2. Data Extraction Mechanism

### Recommended Approach: Python with BeautifulSoup4 + Requests

**Technology Stack:**
- **Python 3.10+**: Main language
- **Requests**: HTTP requests with user-agent headers
- **BeautifulSoup4**: HTML parsing
- **psycopg2** or **SQLAlchemy**: PostgreSQL interface
- **python-json-logger**: Structured logging

**Scraping Strategy:**
1. **List Page Scraping**: Extract listing IDs, basic info, and detect new/changed items
2. **Detail Page Scraping**: Only fetch full details for matching listings
3. **Rate Limiting**: 2-3 second delay between requests to be respectful
4. **Error Handling**: Retry logic with exponential backoff
5. **User-Agent Rotation**: Mimic legitimate browser requests

**Modular Architecture:**
```
scrapers/
├── base_scraper.py       # Abstract base class
├── bazos_scraper.py      # Common Bazos.sk functionality
├── auto_scraper.py       # BMW-specific logic
└── reality_scraper.py    # Real estate-specific logic
```

## 3. Database Schema

### PostgreSQL Tables

#### `categories`
```sql
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'auto', 'reality'
    url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `deals`
```sql
CREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- Bazos listing ID
    category_id INTEGER REFERENCES categories(id),
    title TEXT NOT NULL,
    description TEXT,
    current_price DECIMAL(12,2),
    location VARCHAR(200),
    postal_code VARCHAR(10),
    url VARCHAR(500) NOT NULL,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    last_checked_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    view_count INTEGER,
    metadata JSONB,  -- Flexible storage for category-specific data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deals_external_id ON deals(external_id);
CREATE INDEX idx_deals_category ON deals(category_id);
CREATE INDEX idx_deals_active ON deals(is_active);
CREATE INDEX idx_deals_metadata ON deals USING gin(metadata);
```

#### `price_history`
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
    price DECIMAL(12,2) NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(deal_id, price, changed_at)
);

CREATE INDEX idx_price_history_deal ON price_history(deal_id);
```

#### `deal_images`
```sql
CREATE TABLE deal_images (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `scraping_runs`
```sql
CREATE TABLE scraping_runs (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(50),  -- 'running', 'completed', 'failed'
    listings_processed INTEGER DEFAULT 0,
    new_deals_found INTEGER DEFAULT 0,
    price_changes_detected INTEGER DEFAULT 0,
    error_message TEXT
);
```

## 4. Filtering System

### Configuration Format (JSON)

```json
{
  "scrapers": [
    {
      "name": "BMW E-Series Manual",
      "enabled": true,
      "url": "https://auto.bazos.sk/bmw/",
      "type": "auto",
      "filters": {
        "keywords_required": ["E36", "E46", "E39", "6 valec", "benzin", "manuál"],
        "keywords_excluded": ["havarovan", "nehavarovany", "automat"],
        "price_max": null,
        "price_min": null
      }
    },
    {
      "name": "Large Land Plots",
      "enabled": true,
      "urls": [
        "https://reality.bazos.sk/predam/pozemok/",
        "https://reality.bazos.sk/predam/dom/",
        "https://reality.bazos.sk/predam/chata/"
      ],
      "type": "reality",
      "filters": {
        "price_max": 400000,
        "area_min": 40000,
        "area_units": ["m2", "m²", "metrov", "hektár"],
        "keywords_excluded": ["stavebny pozemok"]
      }
    }
  ],
  "scraping": {
    "request_delay_seconds": 2.5,
    "timeout_seconds": 30,
    "max_retries": 3,
    "user_agents": [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)..."
    ]
  }
}
```

### Filtering Logic

**Auto Listings (BMW):**
- Parse title and description for model codes (E36, E46, E39)
- Match engine type: "6 valec" OR "6 cylinder" OR "6-valec"
- Match fuel type: "benzin" OR "petrol"
- Match transmission: "manuál" OR "manuálna" OR "manual"

**Reality Listings:**
- Extract area from description using regex patterns:
  - `(\d+)\s*(m2|m²|metrov štvorcových)`
  - `(\d+)\s*(ha|hektár|hektárov)` → convert to m²
- Price comparison: `price <= 400000`
- Check both title and description for area info

### Filter Implementation Strategy

**Two-Stage Filtering:**
1. **Quick Filter (List Page)**: Basic keyword matching on title
2. **Deep Filter (Detail Page)**: Comprehensive analysis of full description

**Pattern Matching:**
- Case-insensitive regex
- Handle Slovak language variations (diacritics: á, č, š, etc.)
- Fuzzy matching for common misspellings

## 5. System Architecture

### Components

```
deal_watcher/
├── config/
│   └── config.json              # Scraper configurations
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py          # Abstract base
│   ├── bazos_scraper.py         # Common Bazos logic
│   ├── auto_scraper.py          # Auto-specific
│   └── reality_scraper.py       # Reality-specific
├── filters/
│   ├── __init__.py
│   ├── base_filter.py           # Filter interface
│   ├── auto_filter.py           # BMW filtering logic
│   └── reality_filter.py        # Land size/price filtering
├── database/
│   ├── __init__.py
│   ├── models.py                # SQLAlchemy models
│   ├── migrations/              # Alembic migrations
│   └── repository.py            # Data access layer
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Logging setup
│   └── http_client.py           # Request handling with retries
├── main.py                      # CLI entry point
├── requirements.txt
└── README.md
```

### Execution Flow

1. **Load Configuration**: Read config.json
2. **Initialize Database**: Connect to PostgreSQL
3. **Create Scraping Run**: Log start in `scraping_runs` table
4. **For Each Configured Scraper**:
   - Fetch list pages (paginate through results)
   - Extract listing IDs and basic info
   - Check against database for new/updated listings
   - Apply quick filters
   - For matching listings: fetch detail page
   - Apply deep filters
   - Store/update in database
   - Track price changes
5. **Update Run Status**: Mark completion, log statistics
6. **Output Summary**: Print changes detected

### Output Format (Console)

```
[2025-11-12 10:30:15] Starting scrape run...
[2025-11-12 10:30:15] Category: BMW E-Series Manual
[2025-11-12 10:30:18] Page 1/408 processed - 3 potential matches
[2025-11-12 10:30:45] ✓ NEW: BMW E46 330i Manual - 12,500€ (ID: 184779117)
[2025-11-12 10:31:02] ↓ PRICE DROP: BMW E39 528i - 8,900€ → 8,200€
[2025-11-12 10:45:30] Category complete: 15 new deals, 3 price changes
[2025-11-12 10:45:31] Category: Large Land Plots
[2025-11-12 11:15:20] Category complete: 2 new deals, 0 price changes
[2025-11-12 11:15:20] Scrape run complete - Total: 17 new, 3 updated
```

## 6. Recommendations

### Phase 1 (MVP):
- Implement Bazos.sk scraper for BMW and reality categories
- Basic filtering with JSON config
- PostgreSQL storage with price tracking
- Simple console output
- Cron job setup (every 6-12 hours)

### Phase 2 (Enhancements):
- More sophisticated NLP for filtering (spaCy for Slovak)
- Image downloading and storage
- Email/Telegram notifications for new matches
- Web dashboard for browsing deals
- Additional website modules (Nehnutelnosti.sk, Autobazar.eu)

### Technical Considerations:
- **Rate Limiting**: Essential to avoid IP bans
- **Error Recovery**: Handle network issues gracefully
- **Data Validation**: Verify extracted data before storage
- **Logging**: Comprehensive logs for debugging
- **Monitoring**: Track scraper health and success rates

### Legal/Ethical:
- Review Bazos.sk Terms of Service
- Implement robots.txt compliance
- Use reasonable request rates
- Don't republish scraped content (personal use only)

## 7. Estimated Effort

- **Database Setup**: 2-3 hours
- **Base Scraper Implementation**: 4-6 hours
- **Bazos-specific Scrapers**: 6-8 hours
- **Filtering Logic**: 4-6 hours
- **Testing & Debugging**: 6-8 hours
- **Documentation & Deployment**: 2-3 hours

**Total: ~25-35 hours** for MVP

---

**Next Steps**: Review this document, approve the approach, then proceed with implementation.
