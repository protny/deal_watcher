#!/bin/bash
# Quick setup script for deal_watcher

set -e  # Exit on error

echo "================================================"
echo "Deal Watcher - Quick Setup & First Run"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${GREEN}▶${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Check Python version
print_step "Checking Python version..."
python3 --version || {
    print_error "Python 3 not found"
    exit 1
}

# Step 2: Check if dependencies are installed
print_step "Checking dependencies..."
if ! python3 -c "import requests, bs4, sqlalchemy, psycopg2" 2>/dev/null; then
    print_warning "Some dependencies missing. Installing..."
    pip3 install -r requirements.txt
else
    echo "  ✓ All dependencies installed"
fi

# Step 3: Check for .env file
print_step "Checking environment configuration..."
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "  ✓ Created .env from template"
        echo ""
        print_warning "IMPORTANT: Edit .env and set your DB_CONNECTION_STRING"
        echo "  Example: DB_CONNECTION_STRING=postgresql://user:pass@localhost:5432/deal_watcher"
        echo ""
        read -p "Press Enter when you've updated .env file..."
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    echo "  ✓ .env file exists"
fi

# Step 4: Validate setup
print_step "Running validation checks..."
python3 validate_setup.py || {
    print_error "Validation failed. Please fix issues above."
    exit 1
}

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""

# Ask if user wants to run migration
read -p "Run database migration now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_step "Running database migration..."
    python3 run_migration.py || {
        print_warning "Migration failed. You may need to run it manually."
    }
fi

echo ""
echo "================================================"
echo "Next Steps"
echo "================================================"
echo ""
echo "1. Test the scraper (quick test with 2 pages):"
echo "   python3 -c \"
import json
with open('deal_watcher/config/config.json') as f:
    config = json.load(f)
    for s in config['scrapers']:
        s['max_pages'] = 2
        s['cache_pages'] = True
with open('deal_watcher/config/config.json', 'w') as f:
    json.dump(config, f, indent=2)
   \""
echo "   python -m deal_watcher.main"
echo ""
echo "2. Check results in database:"
echo "   psql -d deal_watcher -c 'SELECT COUNT(*) FROM deals;'"
echo ""
echo "3. View cached pages:"
echo "   ls -lh .cache/pages/"
echo ""
echo "4. For production, restore max_pages to 100 in config.json"
echo ""
echo "5. Set up cron job for automated scraping"
echo ""
