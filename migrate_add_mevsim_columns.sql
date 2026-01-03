-- Migration script to add eski_lastik_mevsim and yeni_lastik_mevsim columns to tire_history table
-- Run this script in your PostgreSQL database

-- Add eski_lastik_mevsim column if it doesn't exist
ALTER TABLE tire_history 
ADD COLUMN IF NOT EXISTS eski_lastik_mevsim VARCHAR(20);

-- Add yeni_lastik_mevsim column if it doesn't exist
ALTER TABLE tire_history 
ADD COLUMN IF NOT EXISTS yeni_lastik_mevsim VARCHAR(20);












