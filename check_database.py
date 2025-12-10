#!/usr/bin/env python3
"""
Script to check database structure and data for seri_no columns
"""
import os
import sys
from sqlalchemy import create_engine, text, inspect
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

def check_database():
    """Check database structure and data"""
    try:
        with engine.connect() as conn:
            # Check tires table structure
            print("=" * 60)
            print("1. TIRES TABLE STRUCTURE")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'tires'
                ORDER BY ordinal_position;
            """))
            for row in result:
                print(f"  {row[0]:30} {row[1]:20} nullable={row[2]} default={row[3]}")
            
            # Check tire_history table structure
            print("\n" + "=" * 60)
            print("2. TIRE_HISTORY TABLE STRUCTURE")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'tire_history'
                ORDER BY ordinal_position;
            """))
            for row in result:
                print(f"  {row[0]:30} {row[1]:20} nullable={row[2]} default={row[3]}")
            
            # Check recent tires
            print("\n" + "=" * 60)
            print("3. RECENT TIRES (last 5)")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT id, seri_no, musteri_id, giris_tarihi, durum
                FROM tires
                ORDER BY giris_tarihi DESC
                LIMIT 5;
            """))
            for row in result:
                print(f"  ID: {row[0]}, Seri No: {row[1]}, Müşteri ID: {row[2]}, Tarih: {row[3]}, Durum: {row[4]}")
            
            # Check recent tire_history
            print("\n" + "=" * 60)
            print("4. RECENT TIRE_HISTORY (last 5)")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT id, musteri_adi, islem_turu, eski_seri_no, yeni_seri_no, islem_tarihi
                FROM tire_history
                ORDER BY islem_tarihi DESC
                LIMIT 5;
            """))
            for row in result:
                print(f"  ID: {row[0]}, Müşteri: {row[1]}, İşlem: {row[2]}")
                print(f"    Eski Seri No: {row[3]}, Yeni Seri No: {row[4]}, Tarih: {row[5]}")
            
            # Check if seri_no column exists in tires
            print("\n" + "=" * 60)
            print("5. CHECKING SERI_NO COLUMN IN TIRES")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(seri_no) as with_seri_no,
                       COUNT(*) - COUNT(seri_no) as without_seri_no
                FROM tires;
            """))
            for row in result:
                print(f"  Toplam kayıt: {row[0]}")
                print(f"  Seri No olan: {row[1]}")
                print(f"  Seri No olmayan: {row[2]}")
            
            # Check max seri_no
            print("\n" + "=" * 60)
            print("6. MAX SERI_NO VALUE")
            print("=" * 60)
            result = conn.execute(text("""
                SELECT MAX(seri_no) as max_seri_no
                FROM tires;
            """))
            for row in result:
                print(f"  Max Seri No: {row[0]}")
            
    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    check_database()










