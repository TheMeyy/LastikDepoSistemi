-- Migration script to add seri_no column to tires table and eski_seri_no/yeni_seri_no to tire_history table
-- Run this script in your PostgreSQL database

-- Add seri_no to tires table
ALTER TABLE tires 
ADD COLUMN IF NOT EXISTS seri_no INTEGER;

-- Set initial serial numbers for existing records (use id as initial value)
UPDATE tires 
SET seri_no = id 
WHERE seri_no IS NULL;

-- Make seri_no unique and not null
ALTER TABLE tires 
ALTER COLUMN seri_no SET NOT NULL;

-- Create unique index on seri_no
CREATE UNIQUE INDEX IF NOT EXISTS tires_seri_no_key ON tires(seri_no);

-- Add eski_seri_no and yeni_seri_no to tire_history table
ALTER TABLE tire_history 
ADD COLUMN IF NOT EXISTS eski_seri_no INTEGER;

ALTER TABLE tire_history 
ADD COLUMN IF NOT EXISTS yeni_seri_no INTEGER;

-- Migration completed successfully!









