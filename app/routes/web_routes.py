from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.models.database import get_db
from app.models.models import Tire, Customer, Rack, Brand, TireSize, TireHistory
from app.models.models import TireDurumEnum as ModelTireDurumEnum, DisDurumuEnum as ModelDisDurumuEnum, MevsimEnum as ModelMevsimEnum
from app.utils.enums import BRAND_LIST, TIRE_SIZES, TireDurumEnum, DisDurumuEnum
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import os
import unicodedata
import re


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

router = APIRouter()

# Setup Jinja2 templates
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))
templates = env


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """Redirect to lastik-ara"""
    # Get brands and tire sizes from database
    brands = db.query(Brand).order_by(Brand.marka_adi).all()
    brand_list = [brand.marka_adi for brand in brands]
    
    tire_sizes = db.query(TireSize).order_by(TireSize.ebat).all()
    tire_size_list = [size.ebat for size in tire_sizes]
    
    query_params = {
        "customer_name": "",
        "plate": "",
        "ebat": "",
        "brand": "",
        "dis_durumu": "",
        "status": "Depoda",  # Default to "Depoda"
        "entry_date_from": "",
        "exit_date_from": ""
    }
    template = templates.get_template("index.html")
    return HTMLResponse(content=template.render(
        request=request,
        tires=[],
        brands=brand_list,
        tire_sizes=tire_size_list,
        query_params=query_params,
        current_path="/"
    ))


@router.get("/lastik-ara", response_class=HTMLResponse)
async def lastik_ara(
    request: Request,
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    ebat: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    dis_durumu: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    seri_no: Optional[str] = Query(None),
    entry_date_from: Optional[str] = Query(None),
    exit_date_from: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Main page - Search and filter tires"""
    try:
        # Build query - use text() to avoid enum conversion issues
        from sqlalchemy import text
        query = db.query(Tire).options(
            joinedload(Tire.brand),
            joinedload(Tire.customer),
            joinedload(Tire.rack)
        )
        
        # Determine status filter logic
        # Default: only show DEPODA tires if status is not specified
        # If status is "Tümü", show all tires
        # If status is "Depoda" or "Çıkmış", apply that filter
        status_clean = ""
        if status:
            try:
                status_clean = status.strip().lower() if status.strip() else ""
            except AttributeError:
                status_clean = str(status).lower() if status else ""
        
        apply_status_filter = True
        status_filter_value = None
        
        if not status or status_clean == "":
            # Default: only show DEPODA tires
            status_filter_value = ModelTireDurumEnum.DEPODA
        elif status_clean in ["tümü", "tumu", "all"]:
            # Show all tires - don't apply status filter
            apply_status_filter = False
        elif status_clean in ["çıkmış", "cikti"]:
            # Show only CIKTI tires
            status_filter_value = ModelTireDurumEnum.CIKTI
        elif status_clean in ["depoda"]:
            # Show only DEPODA tires
            status_filter_value = ModelTireDurumEnum.DEPODA
        
        # Apply status filter if needed
        if apply_status_filter and status_filter_value is not None:
            query = query.filter(Tire.durum == status_filter_value)
        
        # Apply filters
        if customer_name:
            # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
            normalized_search = normalize_turkish_text(customer_name.strip())
            # Tüm müşterileri al ve normalize ederek karşılaştır
            all_customers = db.query(Customer).all()
            matching_customers = []
            for c in all_customers:
                normalized_db_name = normalize_turkish_text(c.ad_soyad or "")
                if normalized_search in normalized_db_name:
                    matching_customers.append(c)
            
            if matching_customers:
                customer_ids = [c.id for c in matching_customers]
                query = query.filter(Tire.musteri_id.in_(customer_ids))
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if plate:
            customer = db.query(Customer).filter(Customer.plaka.ilike(f"%{plate}%")).first()
            if customer:
                query = query.filter(Tire.musteri_id == customer.id)
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if ebat:
            # Filter by any tire size (tire1_size through tire6_size or legacy ebat field)
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Tire.ebat.ilike(f"%{ebat}%"),
                    Tire.tire1_size.ilike(f"%{ebat}%"),
                    Tire.tire2_size.ilike(f"%{ebat}%"),
                    Tire.tire3_size.ilike(f"%{ebat}%"),
                    Tire.tire4_size.ilike(f"%{ebat}%"),
                    Tire.tire5_size.ilike(f"%{ebat}%"),
                    Tire.tire6_size.ilike(f"%{ebat}%")
                )
            )
        
        if brand:
            brand_obj = db.query(Brand).filter(Brand.marka_adi == brand).first()
            if brand_obj:
                query = query.filter(Tire.marka_id == brand_obj.id)
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if dis_durumu:
            try:
                # Try to convert string to enum
                # ModelDisDurumuEnum values are: "İyi", "Orta", "Kötü"
                dis_durum_str = dis_durumu.strip()
                # Try to find matching enum value
                dis_durum_enum = None
                for enum_val in ModelDisDurumuEnum:
                    if enum_val.value == dis_durum_str:
                        dis_durum_enum = enum_val
                        break
                
                if dis_durum_enum:
                    query = query.filter(Tire.dis_durumu == dis_durum_enum)
            except (ValueError, AttributeError, TypeError) as e:
                # Log error but don't fail - just skip this filter
                print(f"Error filtering by dis_durumu: {e}")
                pass
        
        # Status filter is already applied above, no need to apply again here
        
        # Filter by entry date (giris_tarihi)
        # If a single date is selected, filter for that specific day (start and end of day)
        if entry_date_from and entry_date_from.strip():
            try:
                # Handle both ISO format and YYYY-MM-DD format
                date_str = entry_date_from.strip()
                if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                    date_from = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # YYYY-MM-DD format
                    date_from = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Set to start of day (00:00:00)
                date_from_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
                # Set to end of day (23:59:59.999999)
                date_from_end = date_from.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Filter for entries on this specific day
                query = query.filter(
                    Tire.giris_tarihi >= date_from_start,
                    Tire.giris_tarihi <= date_from_end
                )
                print(f"DEBUG: Filtering by entry_date_from: {date_from_start} to {date_from_end}")
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: Error parsing entry_date_from '{entry_date_from}': {e}")
                pass
        
        # Filter by exit date (cikis_tarihi)
        # If a single date is selected, filter for that specific day (start and end of day)
        # Note: Only filter if cikis_tarihi is not NULL
        if exit_date_from and exit_date_from.strip():
            try:
                # Handle both ISO format and YYYY-MM-DD format
                date_str = exit_date_from.strip()
                if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                    date_exit = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # YYYY-MM-DD format
                    date_exit = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Set to start of day (00:00:00)
                date_exit_start = date_exit.replace(hour=0, minute=0, second=0, microsecond=0)
                # Set to end of day (23:59:59.999999)
                date_exit_end = date_exit.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                # Filter for exits on this specific day (only where cikis_tarihi is not NULL)
                from sqlalchemy import and_
                query = query.filter(
                    and_(
                        Tire.cikis_tarihi.isnot(None),  # Ensure cikis_tarihi is not NULL
                        Tire.cikis_tarihi >= date_exit_start,
                        Tire.cikis_tarihi <= date_exit_end
                    )
                )
                print(f"DEBUG: Filtering by exit_date_from: {date_exit_start} to {date_exit_end}")
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: Error parsing exit_date_from '{exit_date_from}': {e}")
                pass
        
        # Filter by serial number
        if seri_no and seri_no.strip():
            try:
                seri_no_int = int(seri_no.strip())
                query = query.filter(Tire.seri_no == seri_no_int)
            except (ValueError, TypeError):
                # If seri_no is not a valid integer, skip this filter
                pass
        
        # Production date filters (year as string)
        # Order by entry date descending
        query = query.order_by(Tire.giris_tarihi.desc())
        
        # Get results - wrap in try-except to handle enum conversion errors
        try:
            tires = query.all()
            print(f"Successfully got {len(tires)} tires from query")
        except (LookupError, ValueError, AttributeError) as enum_error:
            # If enum conversion fails, try to get tires without enum conversion
            print(f"Enum conversion error: {enum_error}, trying alternative approach")
            # Use raw SQL to get durum as text
            from sqlalchemy import text
            try:
                # Get tire IDs first
                tire_ids_query = db.query(Tire.id)
                # Only apply status filter if needed (not "Tümü")
                if apply_status_filter and status_filter_value is not None:
                    tire_ids_query = tire_ids_query.filter(Tire.durum == status_filter_value)
                # If apply_status_filter is False, don't filter by status (show all)
                # Apply other filters...
                if customer_name:
                    # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
                    normalized_search = normalize_turkish_text(customer_name)
                    # Tüm müşterileri al ve normalize ederek karşılaştır
                    all_customers = db.query(Customer).all()
                    matching_customers = [
                        c for c in all_customers 
                        if normalized_search in normalize_turkish_text(c.ad_soyad)
                    ]
                    if matching_customers:
                        customer_ids = [c.id for c in matching_customers]
                        tire_ids_query = tire_ids_query.filter(Tire.musteri_id.in_(customer_ids))
                    else:
                        tire_ids_query = tire_ids_query.filter(Tire.id == -1)  # No results
                if plate:
                    customer = db.query(Customer).filter(Customer.plaka.ilike(f"%{plate}%")).first()
                    if customer:
                        tire_ids_query = tire_ids_query.filter(Tire.musteri_id == customer.id)
                    else:
                        tire_ids_query = tire_ids_query.filter(Tire.id == -1)
                if ebat:
                    tire_ids_query = tire_ids_query.filter(Tire.ebat.ilike(f"%{ebat}%"))
                if brand:
                    brand_obj = db.query(Brand).filter(Brand.marka_adi == brand).first()
                    if brand_obj:
                        tire_ids_query = tire_ids_query.filter(Tire.marka_id == brand_obj.id)
                    else:
                        tire_ids_query = tire_ids_query.filter(Tire.id == -1)
                if entry_date_from and entry_date_from.strip():
                    try:
                        date_str = entry_date_from.strip()
                        if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                            date_from = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            date_from = datetime.strptime(date_str, '%Y-%m-%d')
                        date_from_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
                        date_from_end = date_from.replace(hour=23, minute=59, second=59, microsecond=999999)
                        tire_ids_query = tire_ids_query.filter(
                            Tire.giris_tarihi >= date_from_start,
                            Tire.giris_tarihi <= date_from_end
                        )
                    except (ValueError, AttributeError):
                        pass
                if exit_date_from and exit_date_from.strip():
                    try:
                        date_str = exit_date_from.strip()
                        if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                            date_exit = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                            date_exit = datetime.strptime(date_str, '%Y-%m-%d')
                        date_exit_start = date_exit.replace(hour=0, minute=0, second=0, microsecond=0)
                        date_exit_end = date_exit.replace(hour=23, minute=59, second=59, microsecond=999999)
                        from sqlalchemy import and_
                        tire_ids_query = tire_ids_query.filter(
                            and_(
                                Tire.cikis_tarihi.isnot(None),  # Ensure cikis_tarihi is not NULL
                                Tire.cikis_tarihi >= date_exit_start,
                                Tire.cikis_tarihi <= date_exit_end
                            )
                        )
                    except (ValueError, AttributeError):
                        pass
                
                tire_ids_query = tire_ids_query.order_by(Tire.giris_tarihi.desc())
                tire_ids = [row.id for row in tire_ids_query.all()]
                print(f"Alternative approach: Found {len(tire_ids)} tire IDs, apply_status_filter={apply_status_filter}")
                
                # Now get full Tire objects - handle empty list case
                if tire_ids:
                    tires = db.query(Tire).options(
                        joinedload(Tire.brand),
                        joinedload(Tire.customer),
                        joinedload(Tire.rack)
                    ).filter(Tire.id.in_(tire_ids)).all()
                    print(f"Alternative approach: Successfully loaded {len(tires)} tires")
                else:
                    print("Alternative approach: No tire IDs found, returning empty list")
                    tires = []
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
                tires = []
        
        # Format tire data for template
        tire_list = []
        for tire in tires:
            # Safely convert tire.durum to display string
            durum_display = "Depoda"  # Default
            try:
                # Use getattr with default to avoid attribute errors
                durum_raw = getattr(tire, 'durum', None)
                if durum_raw is None:
                    durum_display = "Depoda"
                elif isinstance(durum_raw, ModelTireDurumEnum):
                    if durum_raw == ModelTireDurumEnum.DEPODA:
                        durum_display = "Depoda"
                    elif durum_raw == ModelTireDurumEnum.CIKTI:
                        durum_display = "Çıkmış"
                elif isinstance(durum_raw, str):
                    durum_str = durum_raw.strip().upper()
                    if durum_str == "DEPODA":
                        durum_display = "Depoda"
                    elif durum_str == "CIKTI":
                        durum_display = "Çıkmış"
                elif hasattr(durum_raw, 'value'):
                    durum_value = durum_raw.value
                    if isinstance(durum_value, str):
                        durum_str = durum_value.strip().upper()
                        if durum_str == "DEPODA":
                            durum_display = "Depoda"
                        elif durum_str == "CIKTI":
                            durum_display = "Çıkmış"
            except Exception as e:
                print(f"Error converting tire.durum: {e}, type: {type(getattr(tire, 'durum', None))}, value: {getattr(tire, 'durum', None)}")
                durum_display = "Depoda"
            
            # Parse not field to separate brand_note and general_note
            # Format: brand_note + "\n\n" + general_note
            not_value = tire.not_ if tire.not_ else ""
            brand_note = ""
            general_note = ""
            if not_value:
                parts = not_value.split("\n\n", 1)
                brand_note = parts[0] if len(parts) > 0 else ""
                general_note = parts[1] if len(parts) > 1 else ""
            
            # Collect all tire sizes and production dates (only those that exist)
            tire_sizes_list = []
            tire_production_dates_list = []
            tire_brands_list = []
            tire_mevsim_list = []
            mevsim_display = ""
            
            # Check tire1 through tire6
            for i in range(1, 7):
                size_field = getattr(tire, f'tire{i}_size', None)
                prod_date_field = getattr(tire, f'tire{i}_production_date', None)
                brand_field = getattr(tire, f'tire{i}_brand', None)
                mevsim_field = getattr(tire, f'tire{i}_mevsim', None) or getattr(tire, 'mevsim', None)
                
                if size_field:
                    tire_sizes_list.append(size_field)
                    tire_production_dates_list.append(prod_date_field if prod_date_field else None)
                    tire_brands_list.append(brand_field if brand_field else (tire.brand.marka_adi if tire.brand else ""))
                    if isinstance(mevsim_field, ModelMevsimEnum):
                        tire_mevsim_list.append(mevsim_field.value)
                    elif hasattr(mevsim_field, 'value'):
                        tire_mevsim_list.append(mevsim_field.value)
                    else:
                        tire_mevsim_list.append(mevsim_field)
            
            # If no tire sizes found in tire1-tire6, use legacy ebat field
            if not tire_sizes_list and tire.ebat:
                tire_sizes_list.append(tire.ebat)
                tire_production_dates_list.append(None)
                tire_brands_list.append(tire.brand.marka_adi if tire.brand else "")
                tire_mevsim_list.append(mevsim_display)
            
            # Get mevsim (season) value - convert enum to display string
            mevsim_display = ""
            try:
                mevsim_raw = getattr(tire, 'mevsim', None)
                if mevsim_raw:
                    # Check if it's an enum instance (ModelMevsimEnum or any enum)
                    if isinstance(mevsim_raw, ModelMevsimEnum):
                        mevsim_display = mevsim_raw.value
                    # Check if it has a 'value' attribute (enum objects)
                    elif hasattr(mevsim_raw, 'value'):
                        mevsim_display = mevsim_raw.value
                    # If it's already a string, use it directly
                    elif isinstance(mevsim_raw, str):
                        mevsim_display = mevsim_raw
                    else:
                        # Handle enum string representation like "MevsimEnum.YAZ" or "MevsimEnum('Yaz')"
                        mevsim_str = str(mevsim_raw)
                        mevsim_str_upper = mevsim_str.upper()
                        
                        # Try to extract value from enum representation using regex
                        import re
                        # Match patterns like "MevsimEnum('Yaz')" or "MevsimEnum.YAZ" or "Yaz"
                        match = re.search(r"['\"]([^'\"]+)['\"]", mevsim_str)
                        if match:
                            extracted_value = match.group(1)
                            # Map to correct display value
                            if extracted_value.upper() in ['YAZ', 'Yaz']:
                                mevsim_display = "Yaz"
                            elif extracted_value.upper() in ['KIS', 'KIŞ', 'Kış']:
                                mevsim_display = "Kış"
                            elif '4' in extracted_value.upper() or 'DORT' in extracted_value.upper():
                                mevsim_display = "4 Mevsim"
                            else:
                                mevsim_display = extracted_value
                        elif 'YAZ' in mevsim_str_upper:
                            mevsim_display = "Yaz"
                        elif 'KIS' in mevsim_str_upper or 'KIŞ' in mevsim_str_upper:
                            mevsim_display = "Kış"
                        elif 'DORT_MEVSIM' in mevsim_str_upper or '4 MEVSIM' in mevsim_str_upper or ('4' in mevsim_str_upper and 'MEVSIM' in mevsim_str_upper):
                            mevsim_display = "4 Mevsim"
                        else:
                            # Last resort: use string representation but clean it up
                            mevsim_display = mevsim_str
            except Exception as e:
                print(f"Error converting tire.mevsim: {e}, type: {type(getattr(tire, 'mevsim', None))}, value: {getattr(tire, 'mevsim', None)}")
                mevsim_display = ""
            
            tire_dict = {
                "id": tire.id,
                "seri_no": tire.seri_no if hasattr(tire, 'seri_no') and tire.seri_no else None,
                "customer_id": tire.musteri_id,  # Add customer_id for filtering
                "customer_name": tire.customer.ad_soyad if tire.customer else "",
                "customer_plate": tire.customer.plaka if tire.customer else "",
                "ebat": tire.ebat,  # Keep for backward compatibility
                "tire_sizes": tire_sizes_list,  # List of all tire sizes
                "tire_production_dates": tire_production_dates_list,  # List of production dates
                "tire_brands": tire_brands_list,
                "tire_mevsims": tire_mevsim_list,
                "brand": tire.brand.marka_adi if tire.brand else (tire_brands_list[0] if tire_brands_list else ""),
                "mevsim": mevsim_display if mevsim_display else (tire_mevsim_list[0] if tire_mevsim_list else ""),
                "rack_code": tire.rack.kod if tire.rack else "",
                "giris_tarihi": tire.giris_tarihi,
                "cikis_tarihi": tire.cikis_tarihi,
                "durum": durum_display,
                "brand_note": brand_note,
                "general_note": general_note
            }
            tire_list.append(tire_dict)
        
        # Filter: Keep only the latest tire per customer (by giris_tarihi)
        # This ensures that when a tire is changed, only the new tire is shown, not the old one
        customer_latest_tire = {}  # {customer_id: tire_dict}
        for tire_dict in tire_list:
            customer_id = tire_dict.get("customer_id")
            if customer_id:
                # If we haven't seen this customer, or this tire is newer, keep it
                if customer_id not in customer_latest_tire:
                    customer_latest_tire[customer_id] = tire_dict
                else:
                    # Compare giris_tarihi - keep the one with the latest date
                    existing_date = customer_latest_tire[customer_id].get("giris_tarihi")
                    current_date = tire_dict.get("giris_tarihi")
                    if existing_date and current_date:
                        if current_date > existing_date:
                            customer_latest_tire[customer_id] = tire_dict
                    elif current_date:  # If existing doesn't have date but current does, use current
                        customer_latest_tire[customer_id] = tire_dict
        
        # Replace tire_list with filtered version (only latest per customer)
        tire_list = list(customer_latest_tire.values())
        # Sort by giris_tarihi descending again (in case order changed)
        # Use a very old date for None values to ensure they go to the end
        tire_list.sort(key=lambda x: x.get("giris_tarihi") or datetime(1900, 1, 1), reverse=True)
        
        # Prepare query params for template
        # If status is None or empty, default to "Depoda" for display
        display_status = "Depoda"
        if status and status.strip():
            status_lower = status.strip().lower()
            if status_lower in ["tümü", "tumu", "all"]:
                display_status = "Tümü"
            elif status_lower in ["çıkmış", "cikti"]:
                display_status = "Çıkmış"
            elif status_lower in ["depoda"]:
                display_status = "Depoda"
        
        query_params = {
            "customer_name": customer_name or "",
            "plate": plate or "",
            "ebat": ebat or "",
            "brand": brand or "",
            "dis_durumu": dis_durumu or "",
            "status": display_status,
            "seri_no": seri_no.strip() if seri_no and seri_no.strip() else "",
            "entry_date_from": entry_date_from or "",
            "exit_date_from": exit_date_from or ""
        }
    
        # Get brands and tire sizes from database
        brands = db.query(Brand).order_by(Brand.marka_adi).all()
        brand_list = [brand.marka_adi for brand in brands]
        
        tire_sizes = db.query(TireSize).order_by(TireSize.ebat).all()
        tire_size_list = [size.ebat for size in tire_sizes]
        
        template = templates.get_template("index.html")
        return HTMLResponse(content=template.render(
            request=request,
            tires=tire_list,
            brands=brand_list,
            tire_sizes=tire_size_list,
            query_params=query_params,
            current_path="/lastik-ara"
        ))
    except Exception as e:
        # Log the error and return a proper error page
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in lastik_ara route: {error_trace}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/yeni-lastik", response_class=HTMLResponse)
async def yeni_lastik(
    request: Request,
    tire_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """New tire entry page - can be pre-filled with existing tire data"""
    # Get racks - if tire_id provided, include the current rack even if full
    from app.utils.enums import RackDurumEnum
    racks_query = db.query(Rack).filter(Rack.durum == RackDurumEnum.BOS)
    
    # If tire_id provided, also include the current rack
    current_rack_id = None
    if tire_id:
        tire = db.query(Tire).filter(Tire.id == tire_id).first()
        if tire and tire.raf_id:
            from sqlalchemy import or_
            current_rack_id = tire.raf_id
            racks_query = db.query(Rack).filter(
                or_(
                    Rack.durum == RackDurumEnum.BOS,
                    Rack.id == tire.raf_id
                )
            )
    
    racks = racks_query.order_by(Rack.kod).all()
    rack_list = [{"id": r.id, "kod": r.kod, "durum": r.durum.value if hasattr(r.durum, 'value') else str(r.durum)} for r in racks]
    
    # Get brands and tire sizes from database
    brands = db.query(Brand).order_by(Brand.marka_adi).all()
    brand_list = [brand.marka_adi for brand in brands]
    
    tire_sizes = db.query(TireSize).order_by(TireSize.ebat).all()
    tire_size_list = [size.ebat for size in tire_sizes]
    
    # If tire_id provided, load existing tire data
    existing_tire_data = None
    if tire_id:
        try:
            tire = db.query(Tire).options(
                joinedload(Tire.brand),
                joinedload(Tire.customer),
                joinedload(Tire.rack)
            ).filter(Tire.id == tire_id).first()
            
            if tire:
                # Collect tire sizes
                tire_sizes_list = []
                tire_production_dates_list = []
                tire_brands_list = []
                tire_mevsim_list = []
                mevsim_display = ""
                for i in range(1, 7):
                    size = getattr(tire, f'tire{i}_size', None)
                    prod_date = getattr(tire, f'tire{i}_production_date', None)
                    brand_val = getattr(tire, f'tire{i}_brand', None) or (tire.brand.marka_adi if tire.brand else "")
                    mevsim_val = getattr(tire, f'tire{i}_mevsim', None) or getattr(tire, 'mevsim', None)
                    if size:
                        tire_sizes_list.append(size)
                        tire_production_dates_list.append(prod_date)
                        tire_brands_list.append(brand_val)
                        if hasattr(mevsim_val, 'value'):
                            tire_mevsim_list.append(mevsim_val.value)
                        else:
                            tire_mevsim_list.append(mevsim_val)
                
                # If no tire sizes in tire1-tire6, use legacy ebat
                if not tire_sizes_list and tire.ebat:
                    tire_sizes_list.append(tire.ebat)
                    tire_production_dates_list.append(None)
                    tire_brands_list.append(tire.brand.marka_adi if tire.brand else "")
                    tire_mevsim_list.append(tire.mevsim.value if hasattr(tire.mevsim, 'value') else str(tire.mevsim))
                
                # Parse not field
                not_value = tire.not_ if tire.not_ else ""
                brand_note = ""
                general_note = ""
                if not_value:
                    parts = not_value.split("\n\n", 1)
                    brand_note = parts[0] if len(parts) > 0 else ""
                    general_note = parts[1] if len(parts) > 1 else ""
                
                existing_tire_data = {
                    "tire_id": tire.id,
                    "customer_name": tire.customer.ad_soyad if tire.customer else "",
                    "customer_plate": tire.customer.plaka if tire.customer else "",
                    "customer_phone": tire.customer.telefon if tire.customer else "",
                    "musteri_id": tire.musteri_id,
                    "brand": tire.brand.marka_adi if tire.brand else "",
                    "mevsim": tire.mevsim.value if hasattr(tire.mevsim, 'value') else str(tire.mevsim),
                    "dis_durumu": tire.dis_durumu.value if hasattr(tire.dis_durumu, 'value') else str(tire.dis_durumu),
                    "raf_id": tire.raf_id,
                    "raf_kodu": tire.rack.kod if tire.rack else "",
                    "brand_note": brand_note,
                    "general_note": general_note,
                    "tire_sizes": tire_sizes_list,
                    "tire_production_dates": tire_production_dates_list,
                    "tire_brands": tire_brands_list,
                    "tire_mevsims": tire_mevsim_list
                }
        except Exception as e:
            print(f"Error loading tire data: {e}")
            existing_tire_data = None
    
    template = templates.get_template("yeni_lastik.html")
    return HTMLResponse(content=template.render(
        request=request,
        brands=brand_list,
        tire_sizes=tire_size_list,
        racks=rack_list,
        existing_tire_data=existing_tire_data,
        current_path="/yeni-lastik"
    ))


@router.get("/musteriler", response_class=HTMLResponse)
async def musteriler(
    request: Request,
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    customer_phone: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Customers page with filtering"""
    # Build query
    query = db.query(Customer)
    
    # Apply filters
    if customer_name:
        # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
        normalized_search = normalize_turkish_text(customer_name.strip() if customer_name else "")
        # Tüm müşterileri al ve normalize ederek karşılaştır
        all_customers = db.query(Customer).all()
        matching_customers = [
            c for c in all_customers 
            if normalized_search in normalize_turkish_text(c.ad_soyad or "")
        ]
        if matching_customers:
            customer_ids = [c.id for c in matching_customers]
            query = query.filter(Customer.id.in_(customer_ids))
        else:
            query = query.filter(Customer.id == -1)  # No results
    
    if plate:
        query = query.filter(Customer.plaka.ilike(f"%{plate}%"))
    
    if customer_phone:
        query = query.filter(Customer.telefon.ilike(f"%{customer_phone}%"))
    
    # Get all customers
    customers = query.order_by(Customer.ad_soyad).all()
    
    # Get tire status counts for each customer
    from app.models.models import Tire
    from app.models.models import TireDurumEnum as ModelTireDurumEnum
    
    customer_list = []
    for c in customers:
        # Get all tires for this customer (both DEPODA and CIKTI)
        tires = []  # Initialize tires variable
        depoda_count = 0
        cikmis_count = 0
        
        try:
            tires = db.query(Tire).filter(Tire.musteri_id == c.id).order_by(Tire.giris_tarihi.desc()).all()
            
            # Get latest tire's serial number
            latest_seri_no = None
            if tires:
                latest_tire = tires[0]  # Most recent tire (ordered by giris_tarihi desc)
                if hasattr(latest_tire, 'seri_no') and latest_tire.seri_no:
                    latest_seri_no = latest_tire.seri_no
            
            # Safely count tires by status
            for t in tires:
                try:
                    durum_raw = getattr(t, 'durum', None)
                    if durum_raw is None:
                        depoda_count += 1  # Default to depoda
                    elif isinstance(durum_raw, ModelTireDurumEnum):
                        if durum_raw == ModelTireDurumEnum.DEPODA:
                            depoda_count += 1
                        elif durum_raw == ModelTireDurumEnum.CIKTI:
                            cikmis_count += 1
                    elif isinstance(durum_raw, str):
                        durum_str = durum_raw.strip().upper()
                        if durum_str == "DEPODA":
                            depoda_count += 1
                        elif durum_str == "CIKTI":
                            cikmis_count += 1
                        else:
                            depoda_count += 1  # Default
                    elif hasattr(durum_raw, 'value'):
                        durum_value = durum_raw.value
                        if isinstance(durum_value, str):
                            durum_str = durum_value.strip().upper()
                            if durum_str == "DEPODA":
                                depoda_count += 1
                            elif durum_str == "CIKTI":
                                cikmis_count += 1
                            else:
                                depoda_count += 1  # Default
                        else:
                            depoda_count += 1  # Default
                    else:
                        depoda_count += 1  # Default
                except Exception as e:
                    print(f"Error counting tire status for customer {c.id}: {e}")
                    depoda_count += 1  # Default to depoda
        except Exception as e:
            print(f"Error getting tires for customer {c.id}: {e}")
            depoda_count = 0
            cikmis_count = 0
            tires = []  # Ensure tires is set even on error
        
        customer_list.append({
            "id": c.id,
            "seri_no": latest_seri_no,  # Latest tire's serial number
            "ad_soyad": c.ad_soyad,
            "telefon": c.telefon,
            "plaka": c.plaka,
            "depoda_count": depoda_count,
            "cikmis_count": cikmis_count,
            "total_count": len(tires)
        })
    
    # Prepare query params for template
    query_params = {
        "customer_name": customer_name or "",
        "plate": plate or "",
        "customer_phone": customer_phone or ""
    }
    
    template = templates.get_template("musteriler.html")
    return HTMLResponse(content=template.render(
        request=request,
        customers=customer_list,
        query_params=query_params,
        current_path="/musteriler"
    ))


@router.get("/raflar", response_class=HTMLResponse)
async def raflar(request: Request, db: Session = Depends(get_db)):
    """Racks page"""
    from app.utils.enums import TireDurumEnum
    import re
    
    # Get all racks ordered by code (natural sort)
    racks = db.query(Rack).order_by(Rack.kod).all()
    
    # Group racks by prefix (e.g., A, B, C)
    rack_groups = {}
    for rack in racks:
        # Extract prefix from rack code (e.g., "A1" -> "A", "B4" -> "B")
        match = re.match(r'^([A-Za-z]+)', rack.kod)
        if match:
            prefix = match.group(1)
        else:
            # If no prefix found, use first character
            prefix = rack.kod[0] if rack.kod else "OTHER"
        
        if prefix not in rack_groups:
            rack_groups[prefix] = []
        
        # Get tires in this rack that are still in depot
        tires_in_rack = db.query(Tire).filter(
            Tire.raf_id == rack.id,
            Tire.durum == ModelTireDurumEnum.DEPODA
        ).options(joinedload(Tire.customer)).all()
        
        tire_count = len(tires_in_rack)
        
        # Get customer names from tires in this rack
        customer_names = []
        if tire_count > 0:
            for tire in tires_in_rack:
                if tire.customer:
                    customer_name = tire.customer.ad_soyad
                    if customer_name and customer_name not in customer_names:
                        customer_names.append(customer_name)
        
        # If multiple customers, show first one with count
        customer_display = ""
        if customer_names:
            if len(customer_names) == 1:
                customer_display = customer_names[0]
            else:
                customer_display = f"{customer_names[0]} (+{len(customer_names)-1})"
        
        rack_groups[prefix].append({
            "id": rack.id,
            "kod": rack.kod,
            "durum": rack.durum.value if hasattr(rack.durum, 'value') else str(rack.durum),
            "not_": rack.not_,
            "tire_count": tire_count,
            "customer_name": customer_display
        })
    
    # Sort racks within each group by number (natural sort)
    for prefix in rack_groups:
        rack_groups[prefix].sort(key=lambda x: (
            # Extract number from code for sorting
            int(re.search(r'\d+', x['kod']).group()) if re.search(r'\d+', x['kod']) else 0
        ))
    
    # Convert to list of groups (sorted by prefix)
    rack_groups_list = [
        {
            "prefix": prefix,
            "racks": rack_groups[prefix]
        }
        for prefix in sorted(rack_groups.keys())
    ]
    
    # Calculate total rack count
    total_racks = len(racks)
    
    template = templates.get_template("raflar.html")
    return HTMLResponse(content=template.render(
        request=request,
        rack_groups=rack_groups_list,
        total_racks=total_racks,
        racks=[],  # Keep for backward compatibility
        current_path="/raflar"
    ))


@router.get("/lastik-etiketleri", response_class=HTMLResponse)
async def lastik_etiketleri(
    request: Request,
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Lastik Etiketleri page - List recent tires for label creation"""
    try:
        # Get all tires ordered by entry date descending (most recent first)
        # Use try-except to handle enum conversion errors
        try:
            query = db.query(Tire).options(
                joinedload(Tire.brand),
                joinedload(Tire.customer),
                joinedload(Tire.rack)
            )
            
            # Apply filters
            # Join Customer only if we need to filter by customer fields
            if customer_name or plate:
                query = query.join(Customer)
                if customer_name:
                    # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
                    normalized_search = normalize_turkish_text(customer_name.strip() if customer_name else "")
                    # Tüm müşterileri al ve normalize ederek karşılaştır
                    all_customers = db.query(Customer).all()
                    matching_customer_ids = [
                        c.id for c in all_customers 
                        if normalized_search in normalize_turkish_text(c.ad_soyad or "")
                    ]
                    if matching_customer_ids:
                        query = query.filter(Tire.musteri_id.in_(matching_customer_ids))
                    else:
                        query = query.filter(Tire.id == -1)  # No results
                if plate:
                    query = query.filter(
                        Customer.plaka.ilike(f"%{plate}%")
                    )
            if date_from:
                try:
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(Tire.giris_tarihi >= date_from_obj)
                except ValueError:
                    pass
            if date_to:
                try:
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(Tire.giris_tarihi <= date_to_obj)
                except ValueError:
                    pass
            
            query = query.order_by(Tire.giris_tarihi.desc())
            
            # Limit to last 100 tires for performance
            tires = query.limit(100).all()
        except (LookupError, ValueError, AttributeError) as enum_error:
            # If enum conversion fails, get tire IDs first
            print(f"Enum conversion error in lastik_etiketleri: {enum_error}, trying alternative approach")
            try:
                tire_ids_query = db.query(Tire.id).order_by(Tire.giris_tarihi.desc()).limit(100)
                tire_ids = [row.id for row in tire_ids_query.all()]
                
                if tire_ids:
                    tires = db.query(Tire).options(
                        joinedload(Tire.brand),
                        joinedload(Tire.customer),
                        joinedload(Tire.rack)
                    ).filter(Tire.id.in_(tire_ids)).all()
                else:
                    tires = []
            except Exception as e2:
                print(f"Alternative approach also failed: {e2}")
                tires = []
        
        # Format tire data for template
        tire_list = []
        for tire in tires:
            # Safely convert tire.durum to display string
            durum_display = "Depoda"  # Default
            try:
                durum_raw = getattr(tire, 'durum', None)
                if durum_raw is None:
                    durum_display = "Depoda"
                elif isinstance(durum_raw, ModelTireDurumEnum):
                    if durum_raw == ModelTireDurumEnum.DEPODA:
                        durum_display = "Depoda"
                    elif durum_raw == ModelTireDurumEnum.CIKTI:
                        durum_display = "Çıkmış"
                elif isinstance(durum_raw, str):
                    durum_str = durum_raw.strip().upper()
                    if durum_str == "DEPODA":
                        durum_display = "Depoda"
                    elif durum_str == "CIKTI":
                        durum_display = "Çıkmış"
                elif hasattr(durum_raw, 'value'):
                    durum_value = durum_raw.value
                    if isinstance(durum_value, str):
                        durum_str = durum_value.strip().upper()
                        if durum_str == "DEPODA":
                            durum_display = "Depoda"
                        elif durum_str == "CIKTI":
                            durum_display = "Çıkmış"
            except Exception as e:
                print(f"Error converting tire.durum in lastik_etiketleri: {e}")
                durum_display = "Depoda"
            
            # Collect all tire sizes
            tire_sizes = []
            for i in range(1, 7):
                size = getattr(tire, f'tire{i}_size', None)
                if size and str(size).strip():
                    tire_sizes.append(str(size).strip())
            
            # If no tire sizes found in tire1-tire6, use legacy ebat field
            if not tire_sizes and tire.ebat:
                tire_sizes.append(str(tire.ebat).strip())
            
            # Get rack code
            rack_code = tire.rack.kod if tire.rack else ""
            
            # Get dis durumu (tire condition)
            dis_durumu_display = ""
            try:
                dis_durumu_raw = getattr(tire, 'dis_durumu', None)
                if dis_durumu_raw:
                    if isinstance(dis_durumu_raw, ModelDisDurumuEnum):
                        dis_durumu_display = dis_durumu_raw.value
                    elif isinstance(dis_durumu_raw, str):
                        dis_durumu_display = dis_durumu_raw
                    elif hasattr(dis_durumu_raw, 'value'):
                        dis_durumu_display = dis_durumu_raw.value
            except Exception as e:
                print(f"Error converting dis_durumu: {e}")
                dis_durumu_display = ""
            
            # Get mevsim (season) value - convert enum to display string
            mevsim_display = ""
            try:
                mevsim_raw = getattr(tire, 'mevsim', None)
                if mevsim_raw:
                    # Check if it's an enum instance (ModelMevsimEnum or any enum)
                    if isinstance(mevsim_raw, ModelMevsimEnum):
                        mevsim_display = mevsim_raw.value
                    # Check if it has a 'value' attribute (enum objects)
                    elif hasattr(mevsim_raw, 'value'):
                        mevsim_display = mevsim_raw.value
                    # If it's already a string, use it directly
                    elif isinstance(mevsim_raw, str):
                        mevsim_display = mevsim_raw
                    else:
                        # Handle enum string representation like "MevsimEnum.YAZ" or "MevsimEnum('Yaz')"
                        mevsim_str = str(mevsim_raw)
                        mevsim_str_upper = mevsim_str.upper()
                        
                        # Try to extract value from enum representation using regex
                        import re
                        # Match patterns like "MevsimEnum('Yaz')" or "MevsimEnum.YAZ" or "Yaz"
                        match = re.search(r"['\"]([^'\"]+)['\"]", mevsim_str)
                        if match:
                            extracted_value = match.group(1)
                            # Map to correct display value
                            if extracted_value.upper() in ['YAZ', 'Yaz']:
                                mevsim_display = "Yaz"
                            elif extracted_value.upper() in ['KIS', 'KIŞ', 'Kış']:
                                mevsim_display = "Kış"
                            elif '4' in extracted_value.upper() or 'DORT' in extracted_value.upper():
                                mevsim_display = "4 Mevsim"
                            else:
                                mevsim_display = extracted_value
                        elif 'YAZ' in mevsim_str_upper:
                            mevsim_display = "Yaz"
                        elif 'KIS' in mevsim_str_upper or 'KIŞ' in mevsim_str_upper:
                            mevsim_display = "Kış"
                        elif 'DORT_MEVSIM' in mevsim_str_upper or '4 MEVSIM' in mevsim_str_upper or ('4' in mevsim_str_upper and 'MEVSIM' in mevsim_str_upper):
                            mevsim_display = "4 Mevsim"
                        else:
                            # Last resort: use string representation but clean it up
                            mevsim_display = mevsim_str
            except Exception as e:
                print(f"Error converting tire.mevsim: {e}, type: {type(getattr(tire, 'mevsim', None))}, value: {getattr(tire, 'mevsim', None)}")
                mevsim_display = ""
            
            import json
            tire_list.append({
                "id": tire.id,
                "seri_no": tire.seri_no if hasattr(tire, 'seri_no') and tire.seri_no else None,
                "customer_name": tire.customer.ad_soyad if tire.customer else "",
                "customer_phone": tire.customer.telefon if tire.customer else "",
                "customer_plate": tire.customer.plaka if tire.customer else "",
                "ebat": tire.ebat,
                "tire_sizes": tire_sizes,  # List of all tire sizes
                "tire_sizes_json": json.dumps(tire_sizes) if tire_sizes else "[]",  # JSON string for template
                "brand": tire.brand.marka_adi if tire.brand else "",
                "mevsim": mevsim_display,  # Mevsim bilgisi
                "rack_code": rack_code,
                "dis_durumu": dis_durumu_display,
                "giris_tarihi": tire.giris_tarihi,
                "durum": durum_display
            })
        
        query_params = {
            "customer_name": customer_name or "",
            "plate": plate or "",
            "date_from": date_from or "",
            "date_to": date_to or ""
        }
        
        template = templates.get_template("lastik_etiketleri.html")
        return HTMLResponse(content=template.render(
            request=request,
            tires=tire_list,
            query_params=query_params,
            current_path="/lastik-etiketleri"
        ))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in lastik_etiketleri endpoint: {error_trace}")
        # Return empty list on error
        query_params = {
            "customer_name": "",
            "plate": "",
            "date_from": "",
            "date_to": ""
        }
        template = templates.get_template("lastik_etiketleri.html")
        return HTMLResponse(content=template.render(
            request=request,
            tires=[],
            query_params=query_params,
            current_path="/lastik-etiketleri"
        ))


@router.get("/musteri-gecmisi", response_class=HTMLResponse)
async def musteri_gecmisi(
    request: Request,
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    seri_no: Optional[str] = Query(None),
    eski_giris_tarihi: Optional[str] = Query(None),
    islem_tarihi: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Customer history page"""
    try:
        # Query directly from database
        query = db.query(TireHistory)
        
        if customer_name:
            # Türkçe karakter ve büyük/küçük harf duyarsız arama için normalize et
            normalized_search = normalize_turkish_text(customer_name.strip())
            # Tüm TireHistory kayıtlarını al ve normalize ederek karşılaştır
            all_history_items = db.query(TireHistory).all()
            matching_history_ids = [
                h.id for h in all_history_items 
                if normalized_search in normalize_turkish_text(h.musteri_adi or "")
            ]
            if matching_history_ids:
                query = query.filter(TireHistory.id.in_(matching_history_ids))
            else:
                query = query.filter(TireHistory.id == -1)  # No results
        if plate:
            query = query.filter(TireHistory.plaka.ilike(f"%{plate}%"))
        if phone:
            query = query.filter(TireHistory.telefon.ilike(f"%{phone}%"))
        
        # Filter by serial number - search in both eski_seri_no and yeni_seri_no
        if seri_no:
            seri_no_clean = str(seri_no).strip()
            if seri_no_clean and seri_no_clean != "":
                try:
                    seri_no_int = int(seri_no_clean)
                    # Search in both eski_seri_no and yeni_seri_no columns
                    from sqlalchemy import or_
                    query = query.filter(
                        or_(
                            TireHistory.eski_seri_no == seri_no_int,
                            TireHistory.yeni_seri_no == seri_no_int
                        )
                    )
                    print(f"DEBUG: Filtering by seri_no={seri_no_int}")
                except (ValueError, TypeError) as e:
                    # If seri_no is not a valid integer, skip this filter
                    print(f"Warning: Invalid seri_no value '{seri_no}': {e}")
                    pass
        
        # Filter by dates - separate filters for eski_lastik_giris_tarihi and islem_tarihi
        from sqlalchemy import and_
        
        # Filter by Eski Lastik Giriş Tarihi (eski_lastik_giris_tarihi)
        if eski_giris_tarihi and eski_giris_tarihi.strip():
            try:
                date_str = eski_giris_tarihi.strip()
                if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                date_end = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Filter for entries where eski_lastik_giris_tarihi matches this day
                query = query.filter(
                    and_(
                        TireHistory.eski_lastik_giris_tarihi.isnot(None),
                        TireHistory.eski_lastik_giris_tarihi >= date_start,
                        TireHistory.eski_lastik_giris_tarihi <= date_end
                    )
                )
                print(f"DEBUG: Filtering by eski_giris_tarihi: {date_start} to {date_end}")
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: Error parsing eski_giris_tarihi '{eski_giris_tarihi}': {e}")
                pass
        
        # Filter by Lastik Değişim/Çıkış Tarihi (islem_tarihi)
        if islem_tarihi and islem_tarihi.strip():
            try:
                date_str = islem_tarihi.strip()
                if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                date_end = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                # Filter for entries where islem_tarihi matches this day
                query = query.filter(
                    and_(
                        TireHistory.islem_tarihi >= date_start,
                        TireHistory.islem_tarihi <= date_end
                    )
                )
                print(f"DEBUG: Filtering by islem_tarihi: {date_start} to {date_end}")
            except (ValueError, AttributeError) as e:
                print(f"DEBUG: Error parsing islem_tarihi '{islem_tarihi}': {e}")
                pass
        
        # Try to query with mevsim columns, but handle case where they don't exist yet
        import json
        history_items = []
        try:
            history_items_raw = query.order_by(TireHistory.islem_tarihi.desc()).limit(100).all()
        except Exception as e:
            # If mevsim columns don't exist, query without them using raw SQL
            print(f"Warning: Mevsim columns may not exist. Using fallback query. Error: {e}")
            from sqlalchemy import text
            
            # Build WHERE clause for fallback query
            where_conditions = []
            params = {}
            
            if customer_name:
                where_conditions.append("musteri_adi ILIKE :customer_name")
                params["customer_name"] = f"%{customer_name}%"
            if plate:
                where_conditions.append("plaka ILIKE :plate")
                params["plate"] = f"%{plate}%"
            if phone:
                where_conditions.append("telefon ILIKE :phone")
                params["phone"] = f"%{phone}%"
            if seri_no and seri_no.strip():
                try:
                    seri_no_int = int(seri_no.strip())
                    where_conditions.append("(eski_seri_no = :seri_no OR yeni_seri_no = :seri_no)")
                    params["seri_no"] = seri_no_int
                except (ValueError, TypeError):
                    pass
            # Parse dates for fallback SQL query - use eski_giris_tarihi and islem_tarihi
            eski_giris_date_start = None
            eski_giris_date_end = None
            islem_date_start = None
            islem_date_end = None
            
            if eski_giris_tarihi and eski_giris_tarihi.strip():
                try:
                    date_str = eski_giris_tarihi.strip()
                    if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    eski_giris_date_start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    eski_giris_date_end = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                except (ValueError, AttributeError):
                    pass
            
            if islem_tarihi and islem_tarihi.strip():
                try:
                    date_str = islem_tarihi.strip()
                    if 'T' in date_str or '+' in date_str or 'Z' in date_str:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    else:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    islem_date_start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    islem_date_end = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
                except (ValueError, AttributeError):
                    pass
            
            # Apply date filters to SQL query
            if eski_giris_date_start:
                where_conditions.append("""
                    (eski_lastik_giris_tarihi IS NOT NULL 
                     AND eski_lastik_giris_tarihi >= :eski_giris_date_start 
                     AND eski_lastik_giris_tarihi <= :eski_giris_date_end)
                """)
                params["eski_giris_date_start"] = eski_giris_date_start
                params["eski_giris_date_end"] = eski_giris_date_end
            
            if islem_date_start:
                where_conditions.append("""
                    (islem_tarihi >= :islem_date_start 
                     AND islem_tarihi <= :islem_date_end)
                """)
                params["islem_date_start"] = islem_date_start
                params["islem_date_end"] = islem_date_end
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            sql_query = text(f"""
                SELECT id, musteri_id, musteri_adi, plaka, telefon, islem_turu, islem_tarihi,
                       eski_lastik_ebat, eski_lastik_marka, eski_lastik_giris_tarihi,
                       eski_seri_no, yeni_seri_no,
                       yeni_lastik_ebat, yeni_lastik_marka, yeni_lastik_marka_json, raf_kodu, "not",
                       eski_lastik_mevsim, yeni_lastik_mevsim, yeni_lastik_mevsim_json
                FROM tire_history
                WHERE {where_clause}
                ORDER BY islem_tarihi DESC
                LIMIT 100
            """)
            result = db.execute(sql_query)
            history_items_raw = result.fetchall()
            # Convert to dict-like objects
            class TempHistoryItem:
                def __init__(self, row):
                    self.id = row.id
                    self.musteri_id = row.musteri_id
                    self.musteri_adi = row.musteri_adi
                    self.plaka = row.plaka
                    self.telefon = row.telefon
                    self.islem_turu = row.islem_turu
                    self.islem_tarihi = row.islem_tarihi
                    self.eski_lastik_ebat = row.eski_lastik_ebat
                    self.eski_lastik_marka = row.eski_lastik_marka
                    self.eski_lastik_giris_tarihi = getattr(row, 'eski_lastik_giris_tarihi', None)
                    self.eski_seri_no = getattr(row, 'eski_seri_no', None)
                    self.yeni_seri_no = getattr(row, 'yeni_seri_no', None)
                    self.yeni_lastik_ebat = row.yeni_lastik_ebat
                    self.yeni_lastik_marka = row.yeni_lastik_marka
                    self.yeni_lastik_marka_json = getattr(row, 'yeni_lastik_marka_json', None)
                    self.raf_kodu = row.raf_kodu
                    self.not_ = row.not_
                    self.eski_lastik_mevsim = getattr(row, 'eski_lastik_mevsim', None)
                    self.yeni_lastik_mevsim = getattr(row, 'yeni_lastik_mevsim', None)
                    self.yeni_lastik_mevsim_json = getattr(row, 'yeni_lastik_mevsim_json', None)
            history_items_raw = [TempHistoryItem(row) for row in history_items_raw]
        
        for item in history_items_raw:
            eski_ebat_list = []
            yeni_ebat_list = []
            yeni_marka_list = []
            yeni_mevsim_list = []
            eski_marka_list = []
            eski_mevsim_list = []
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
            # Parse new brand/mevsim json lists if present
            if hasattr(item, 'yeni_lastik_marka_json') and getattr(item, 'yeni_lastik_marka_json', None):
                try:
                    yeni_marka_list = json.loads(item.yeni_lastik_marka_json) or []
                except:
                    yeni_marka_list = []
            if hasattr(item, 'yeni_lastik_mevsim_json') and getattr(item, 'yeni_lastik_mevsim_json', None):
                try:
                    yeni_mevsim_list = json.loads(item.yeni_lastik_mevsim_json) or []
                except:
                    yeni_mevsim_list = []
            
            # Get mevsim values - handle case where columns don't exist yet
            eski_mevsim = None
            yeni_mevsim = None
            try:
                if hasattr(item, 'eski_lastik_mevsim') and item.eski_lastik_mevsim:
                    if hasattr(item.eski_lastik_mevsim, 'value'):
                        eski_mevsim = item.eski_lastik_mevsim.value
                    else:
                        eski_mevsim = str(item.eski_lastik_mevsim)
            except (AttributeError, KeyError):
                pass
            
            try:
                if hasattr(item, 'yeni_lastik_mevsim') and item.yeni_lastik_mevsim:
                    if hasattr(item.yeni_lastik_mevsim, 'value'):
                        yeni_mevsim = item.yeni_lastik_mevsim.value
                    else:
                        yeni_mevsim = str(item.yeni_lastik_mevsim)
            except (AttributeError, KeyError):
                pass
            
            # Get serial numbers - handle case where columns don't exist yet
            eski_seri_no = None
            yeni_seri_no = None
            try:
                if hasattr(item, 'eski_seri_no'):
                    eski_seri_no = item.eski_seri_no
            except (AttributeError, KeyError):
                pass
            
            try:
                if hasattr(item, 'yeni_seri_no'):
                    yeni_seri_no = item.yeni_seri_no
            except (AttributeError, KeyError):
                pass
            
            # Build old brand/mevsim lists to align per tire entry
            if eski_ebat_list:
                if item.eski_lastik_marka:
                    eski_marka_list = [item.eski_lastik_marka] * len(eski_ebat_list)
                if eski_mevsim:
                    eski_mevsim_list = [eski_mevsim] * len(eski_ebat_list)

            # Build new brand/mevsim lists fallback if not provided
            if yeni_ebat_list:
                if not yeni_marka_list and getattr(item, 'yeni_lastik_marka', None):
                    yeni_marka_list = [item.yeni_lastik_marka] * len(yeni_ebat_list)
                if not yeni_mevsim_list and yeni_mevsim:
                    yeni_mevsim_list = [yeni_mevsim] * len(yeni_ebat_list)

            history_items.append({
                "id": item.id,
                "musteri_adi": item.musteri_adi,
                "plaka": item.plaka,
                "telefon": item.telefon,
                "islem_turu": item.islem_turu.value if hasattr(item.islem_turu, 'value') else str(item.islem_turu),
                "islem_tarihi": item.islem_tarihi,
                "eski_lastik_ebat": eski_ebat_list,
                "eski_lastik_marka": item.eski_lastik_marka,
                "eski_lastik_marka_list": eski_marka_list,
                "eski_lastik_mevsim": eski_mevsim,
                "eski_lastik_mevsim_list": eski_mevsim_list,
                "eski_lastik_giris_tarihi": getattr(item, 'eski_lastik_giris_tarihi', None),
                "eski_seri_no": eski_seri_no,
                "yeni_lastik_ebat": yeni_ebat_list,
                "yeni_lastik_marka": item.yeni_lastik_marka,
                "yeni_lastik_marka_list": yeni_marka_list,
                "yeni_lastik_mevsim": yeni_mevsim,
                "yeni_lastik_mevsim_list": yeni_mevsim_list,
                "yeni_seri_no": yeni_seri_no,
                "raf_kodu": item.raf_kodu,
                "not": item.not_
            })
        
        query_params = {
            "customer_name": customer_name or "",
            "plate": plate or "",
            "phone": phone or "",
            "seri_no": seri_no.strip() if seri_no and seri_no.strip() else "",
            "eski_giris_tarihi": eski_giris_tarihi or "",
            "islem_tarihi": islem_tarihi or ""
        }
        
        template = templates.get_template("musteri_gecmisi.html")
        return HTMLResponse(content=template.render(
            request=request,
            history_items=history_items,
            query_params=query_params,
            current_path="/musteri-gecmisi"
        ))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in musteri_gecmisi endpoint: {error_trace}")
        template = templates.get_template("musteri_gecmisi.html")
        return HTMLResponse(content=template.render(
            request=request,
            history_items=[],
            query_params={},
            current_path="/musteri-gecmisi"
        ))
