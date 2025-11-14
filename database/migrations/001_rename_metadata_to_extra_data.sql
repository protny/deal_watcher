-- Migration: Rename metadata column to extra_data
-- This fixes the SQLAlchemy reserved keyword issue

-- Rename the column
ALTER TABLE deals RENAME COLUMN metadata TO extra_data;

-- Drop old index
DROP INDEX IF EXISTS idx_deals_metadata;

-- Create new index
CREATE INDEX IF NOT EXISTS idx_deals_extra_data ON deals USING gin(extra_data);

-- Verify the change
\d deals
