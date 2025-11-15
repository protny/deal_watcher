-- Deal Watcher Database Schema
-- PostgreSQL 12+

-- Categories table: stores different scraping categories
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'auto', 'reality'
    url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deals table: stores all listings
CREATE TABLE IF NOT EXISTS deals (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) UNIQUE NOT NULL,  -- Bazos listing ID
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
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
    extra_data JSONB,  -- Flexible storage for category-specific data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for deals table
CREATE INDEX IF NOT EXISTS idx_deals_external_id ON deals(external_id);
CREATE INDEX IF NOT EXISTS idx_deals_category ON deals(category_id);
CREATE INDEX IF NOT EXISTS idx_deals_active ON deals(is_active);
CREATE INDEX IF NOT EXISTS idx_deals_extra_data ON deals USING gin(extra_data);
CREATE INDEX IF NOT EXISTS idx_deals_first_seen ON deals(first_seen_at);

-- Price history table: tracks price changes over time
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
    price DECIMAL(12,2) NOT NULL,
    changed_at TIMESTAMP DEFAULT NOW()
);

-- Index and unique constraint for price history
CREATE INDEX IF NOT EXISTS idx_price_history_deal ON price_history(deal_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_history_unique ON price_history(deal_id, price, changed_at);

-- Deal images table: stores image URLs for deals
CREATE TABLE IF NOT EXISTS deal_images (
    id SERIAL PRIMARY KEY,
    deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for deal images
CREATE INDEX IF NOT EXISTS idx_deal_images_deal ON deal_images(deal_id);

-- Scraping runs table: tracks scraper execution history
CREATE TABLE IF NOT EXISTS scraping_runs (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running',  -- 'running', 'completed', 'failed'
    listings_processed INTEGER DEFAULT 0,
    new_deals_found INTEGER DEFAULT 0,
    price_changes_detected INTEGER DEFAULT 0,
    deals_disappeared INTEGER DEFAULT 0,
    error_message TEXT
);

-- Index for scraping runs
CREATE INDEX IF NOT EXISTS idx_scraping_runs_status ON scraping_runs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_runs_started ON scraping_runs(started_at DESC);

-- Insert default categories
INSERT INTO categories (name, type, url) VALUES
    ('BMW E-Series', 'auto', 'https://auto.bazos.sk/bmw/'),
    ('Land Plots', 'reality', 'https://reality.bazos.sk/predam/pozemok/'),
    ('Houses', 'reality', 'https://reality.bazos.sk/predam/dom/'),
    ('Cottages', 'reality', 'https://reality.bazos.sk/predam/chata/')
ON CONFLICT DO NOTHING;
