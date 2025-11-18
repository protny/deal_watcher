# Setup Notes

## Fixed Issues

### Scraper HTML Parsing ✓
The original implementation had incorrect HTML selectors for Bazos.sk:
- **Fixed**: Changed `class='inzerat'` → `class='inzeraty'`
- **Fixed**: Title extraction now finds `<h2 class="nadpis"><a>` structure
- **Fixed**: View count extraction now finds `<div class="inzeratyview">`

### SQLAlchemy Reserved Keyword ✓
- **Fixed**: Renamed `metadata` column → `extra_data` (metadata is reserved in SQLAlchemy)
- Updated in: models.py, repository.py, schema.sql

## Test Results

Running `python3 test_scraper.py`:
```
✓ BMW Scraper: Scraped 40 listings from 2 pages
✓ Reality Scraper: Scraped 40 listings from 2 pages
✓ Filters working correctly
✓ Found 1 property matching criteria (≥40,000 m²)
```

## Database Setup (Required for Full System)

The main application requires PostgreSQL. Here's how to set it up:

### 1. Start PostgreSQL

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Create database
sudo -u postgres createdb deal_watcher

# Initialize schema
sudo -u postgres psql -d deal_watcher -f database/schema.sql
```

### 3. Configure Environment

Create `.env` file in project root:

```bash
cat > .env << 'EOF'
DB_CONNECTION_STRING=postgresql://postgres:password@localhost:5432/deal_watcher
LOG_LEVEL=INFO
EOF
```

Replace `password` with your PostgreSQL password, or use peer authentication:

```
DB_CONNECTION_STRING=postgresql:///deal_watcher
```

### 4. Verify Setup

```bash
# Test database connection
psql -d deal_watcher -c "SELECT COUNT(*) FROM categories;"
```

## Running the System

### With Database (Full System)
```bash
python -m deal_watcher.main
```

### Without Database (Test Scraping Only)
```bash
python3 test_scraper.py
```

## Troubleshooting

### "No module named 'bs4'"
```bash
pip3 install -r requirements.txt
```

### "DB_CONNECTION_STRING environment variable not set"
Create `.env` file as shown above.

### "psycopg2.OperationalError: could not connect to server"
Start PostgreSQL service:
```bash
sudo systemctl start postgresql
```

### Test database connection:
```bash
psql -U postgres -d deal_watcher -c "SELECT 1;"
```

## Next Steps

1. ✅ Scraper is working correctly
2. ✅ Filters are functioning
3. ✅ Data extraction validated
4. 📝 Set up PostgreSQL database
5. 📝 Run full system with database
6. 📝 Schedule with cron for automated execution

## Cron Setup Example

Once database is configured, add to crontab:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 6 hours)
0 */6 * * * cd /home/user/deal_watcher && /usr/bin/python3 -m deal_watcher.main >> /var/log/deal_watcher.log 2>&1
```

## Current Status

- ✅ Complete implementation done
- ✅ HTML parsing fixed and tested
- ✅ Scraping functionality verified
- ✅ Filters working correctly
- ⚠️  Database setup required for full system
- ✅ Test mode available (test_scraper.py)
