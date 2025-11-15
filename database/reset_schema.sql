-- Reset schema - WARNING: This will delete all data!

-- Drop all tables
DROP TABLE IF EXISTS scraping_runs CASCADE;
DROP TABLE IF EXISTS deal_images CASCADE;
DROP TABLE IF EXISTS price_history CASCADE;
DROP TABLE IF EXISTS deals CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- Recreate from schema.sql
\i database/schema.sql
