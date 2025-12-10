-- Veritabanı kontrol sorguları
-- Bu sorguları PostgreSQL client'ınızda çalıştırın

-- 1. Tires tablosunda seri_no sütunu var mı?
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tires' AND column_name = 'seri_no';

-- 2. Tire_history tablosunda eski_seri_no ve yeni_seri_no sütunları var mı?
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'tire_history' 
AND (column_name = 'eski_seri_no' OR column_name = 'yeni_seri_no');

-- 3. Son 5 lastik kaydının seri_no değerleri
SELECT id, seri_no, musteri_id, giris_tarihi, durum
FROM tires
ORDER BY giris_tarihi DESC
LIMIT 5;

-- 4. Son 5 tire_history kaydının seri_no değerleri
SELECT id, musteri_adi, islem_turu, eski_seri_no, yeni_seri_no, islem_tarihi
FROM tire_history
ORDER BY islem_tarihi DESC
LIMIT 5;

-- 5. Seri_no NULL olan kayıtlar var mı?
SELECT COUNT(*) as total,
       COUNT(seri_no) as with_seri_no,
       COUNT(*) - COUNT(seri_no) as without_seri_no
FROM tires;

-- 6. En yüksek seri_no değeri
SELECT MAX(seri_no) as max_seri_no
FROM tires;









