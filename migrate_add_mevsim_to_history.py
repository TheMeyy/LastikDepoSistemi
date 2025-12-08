#!/usr/bin/env python3
"""
Migration script to add eski_lastik_mevsim and yeni_lastik_mevsim columns to tire_history table
"""
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("Error: DATABASE_URL not found in .env file")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

def migrate():
    """Add mevsim columns to tire_history table"""
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'tire_history' 
                AND column_name IN ('eski_lastik_mevsim', 'yeni_lastik_mevsim')
            """)
            existing_columns = [row[0] for row in conn.execute(check_query)]
            
            # Add eski_lastik_mevsim column if it doesn't exist
            if 'eski_lastik_mevsim' not in existing_columns:
                print("Adding eski_lastik_mevsim column...")
                conn.execute(text("""
                    ALTER TABLE tire_history 
                    ADD COLUMN eski_lastik_mevsim VARCHAR(20)
                """))
                conn.commit()
                print("✓ eski_lastik_mevsim column added")
            else:
                print("✓ eski_lastik_mevsim column already exists")
            
            # Add yeni_lastik_mevsim column if it doesn't exist
            if 'yeni_lastik_mevsim' not in existing_columns:
                print("Adding yeni_lastik_mevsim column...")
                conn.execute(text("""
                    ALTER TABLE tire_history 
                    ADD COLUMN yeni_lastik_mevsim VARCHAR(20)
                """))
                conn.commit()
                print("✓ yeni_lastik_mevsim column added")
            else:
                print("✓ yeni_lastik_mevsim column already exists")
            
            print("\nMigration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate()







