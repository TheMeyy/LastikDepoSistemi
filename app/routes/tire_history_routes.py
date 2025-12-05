from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.models.database import get_db
from app.models.models import TireHistory, Customer, Tire, Brand
from app.models.models import IslemTuruEnum as ModelIslemTuruEnum
from app.utils.enums import IslemTuruEnum
import json
import unicodedata


def normalize_turkish_text(text: str) -> str:
    """
    Türkçe karakterleri normalize eder ve lowercase'e çevirir.
    Büyük/küçük harf duyarsız ve Türkçe karakter desteği için kullanılır.
    """
    if not text:
        return ""
    # Önce lowercase'e çevir
    text = text.lower()
    # Türkçe karakterleri normalize et (büyük ve küçük harfleri kapsar)
    text = text.replace('ı', 'i')
    text = text.replace('ş', 's')
    text = text.replace('ğ', 'g')
    text = text.replace('ü', 'u')
    text = text.replace('ö', 'o')
    text = text.replace('ç', 'c')
    # Büyük harfli Türkçe karakterleri de normalize et (lowercase sonrası gerekli değil ama güvenlik için)
    text = text.replace('İ', 'i')
    text = text.replace('Ş', 's')
    text = text.replace('Ğ', 'g')
    text = text.replace('Ü', 'u')
    text = text.replace('Ö', 'o')
    text = text.replace('Ç', 'c')
    return text

router = APIRouter(prefix="/api/tire-history", tags=["tire-history"])


@router.get("/")
def get_tire_history(
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get tire history with filters"""
    query = db.query(TireHistory)
    
    if customer_name:
        # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
        normalized_search = normalize_turkish_text(customer_name)
        # Tüm geçmiş kayıtlarını al ve normalize ederek karşılaştır
        all_history = db.query(TireHistory).all()
        matching_history_ids = [
            h.id for h in all_history 
            if normalized_search in normalize_turkish_text(h.musteri_adi)
        ]
        if matching_history_ids:
            query = query.filter(TireHistory.id.in_(matching_history_ids))
        else:
            query = query.filter(TireHistory.id == -1)  # No results
    
    if plate:
        query = query.filter(TireHistory.plaka.ilike(f"%{plate}%"))
    
    if phone:
        query = query.filter(TireHistory.telefon.ilike(f"%{phone}%"))
    
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from)
            query = query.filter(TireHistory.islem_tarihi >= date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to)
            query = query.filter(TireHistory.islem_tarihi <= date_to_obj)
        except ValueError:
            pass
    
    history_items = query.order_by(TireHistory.islem_tarihi.desc()).offset(skip).limit(limit).all()
    
    result = []
    for item in history_items:
        # Parse JSON strings for tire sizes
        eski_ebat_list = []
        yeni_ebat_list = []
        
        if item.eski_lastik_ebat:
            try:
                eski_ebat_list = json.loads(item.eski_lastik_ebat)
            except:
                pass
        
        if item.yeni_lastik_ebat:
            try:
                yeni_ebat_list = json.loads(item.yeni_lastik_ebat)
            except:
                pass
        
        # Get mevsim values
        eski_mevsim = item.eski_lastik_mevsim.value if item.eski_lastik_mevsim and hasattr(item.eski_lastik_mevsim, 'value') else (str(item.eski_lastik_mevsim) if item.eski_lastik_mevsim else None)
        yeni_mevsim = item.yeni_lastik_mevsim.value if item.yeni_lastik_mevsim and hasattr(item.yeni_lastik_mevsim, 'value') else (str(item.yeni_lastik_mevsim) if item.yeni_lastik_mevsim else None)
        
        # Get serial numbers
        eski_seri_no = item.eski_seri_no if hasattr(item, 'eski_seri_no') and item.eski_seri_no else None
        yeni_seri_no = item.yeni_seri_no if hasattr(item, 'yeni_seri_no') and item.yeni_seri_no else None
        
        result.append({
            "id": item.id,
            "musteri_adi": item.musteri_adi,
            "plaka": item.plaka,
            "telefon": item.telefon,
            "islem_turu": item.islem_turu.value if hasattr(item.islem_turu, 'value') else str(item.islem_turu),
            "islem_tarihi": item.islem_tarihi,
            "eski_lastik_ebat": eski_ebat_list,
            "eski_lastik_marka": item.eski_lastik_marka,
            "eski_lastik_mevsim": eski_mevsim,
            "eski_lastik_giris_tarihi": item.eski_lastik_giris_tarihi,
            "eski_seri_no": eski_seri_no,
            "yeni_lastik_ebat": yeni_ebat_list,
            "yeni_lastik_marka": item.yeni_lastik_marka,
            "yeni_lastik_mevsim": yeni_mevsim,
            "yeni_seri_no": yeni_seri_no,
            "raf_kodu": item.raf_kodu,
            "not": item.not_
        })
    
    return {"items": result, "total": len(result)}

