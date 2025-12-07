#!/usr/bin/env python3
"""
Migration script to add seri_no column to tires table and eski_seri_no/yeni_seri_no to tire_history table
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "lastik_depo_db")

DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

def migrate():
    """Add seri_no columns to tires and tire_history tables"""
    try:
        with engine.connect() as conn:
            # Add seri_no to tires table
            print("Adding seri_no column to tires table...")
            conn.execute(text("""
                ALTER TABLE tires 
                ADD COLUMN IF NOT EXISTS seri_no INTEGER;
            """))
            conn.commit()
            
            # Set initial serial numbers for existing records
            print("Setting initial serial numbers for existing tires...")
            conn.execute(text("""
                UPDATE tires 
                SET seri_no = id 
                WHERE seri_no IS NULL;
            """))
            conn.commit()
            
            # Make seri_no unique and not null
            print("Making seri_no unique and not null...")
            conn.execute(text("""
                ALTER TABLE tires 
                ALTER COLUMN seri_no SET NOT NULL;
            """))
            conn.commit()
            
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS tires_seri_no_key ON tires(seri_no);
            """))
            conn.commit()
            
            # Add eski_seri_no and yeni_seri_no to tire_history table
            print("Adding eski_seri_no and yeni_seri_no columns to tire_history table...")
            conn.execute(text("""
                ALTER TABLE tire_history 
                ADD COLUMN IF NOT EXISTS eski_seri_no INTEGER;
            """))
            conn.commit()
            
            conn.execute(text("""
                ALTER TABLE tire_history 
                ADD COLUMN IF NOT EXISTS yeni_seri_no INTEGER;
            """))
            conn.commit()
            
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate()






