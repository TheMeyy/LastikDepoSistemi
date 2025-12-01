from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.models.database import get_db
from app.models.models import Tire, Customer, Rack, Brand
from app.models.models import TireDurumEnum as ModelTireDurumEnum, DisDurumuEnum as ModelDisDurumuEnum
from app.utils.enums import BRAND_LIST, TIRE_SIZES, TireDurumEnum, DisDurumuEnum
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import os

router = APIRouter()

# Setup Jinja2 templates
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
env = Environment(loader=FileSystemLoader(template_dir))
templates = env


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Redirect to lastik-ara"""
    query_params = {
        "customer_name": "",
        "plate": "",
        "customer_phone": "",
        "ebat": "",
        "brand": "",
        "dis_durumu": "",
        "status": "Depoda",  # Default to "Depoda"
        "entry_date_from": "",
        "entry_date_to": ""
    }
    template = templates.get_template("index.html")
    return HTMLResponse(content=template.render(
        request=request,
        tires=[],
        brands=BRAND_LIST,
        tire_sizes=TIRE_SIZES,
        query_params=query_params,
        current_path="/"
    ))


@router.get("/lastik-ara", response_class=HTMLResponse)
async def lastik_ara(
    request: Request,
    customer_name: Optional[str] = Query(None),
    plate: Optional[str] = Query(None),
    customer_phone: Optional[str] = Query(None),
    ebat: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    dis_durumu: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    entry_date_from: Optional[str] = Query(None),
    entry_date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Main page - Search and filter tires"""
    try:
        # Build query
        query = db.query(Tire).options(
            joinedload(Tire.brand),
            joinedload(Tire.customer),
            joinedload(Tire.rack)
        )
        
        # Determine status filter logic
        # Default: only show DEPODA tires if status is not specified
        # If status is "Tümü", show all tires
        # If status is "Depoda" or "Çıkmış", apply that filter
        status_clean = status.strip().lower() if status and status.strip() else ""
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
        if apply_status_filter and status_filter_value:
            query = query.filter(Tire.durum == status_filter_value)
        
        # Apply filters
        if customer_name:
            customers = db.query(Customer).filter(
                Customer.ad_soyad.ilike(f"%{customer_name}%")
            ).all()
            if customers:
                customer_ids = [c.id for c in customers]
                query = query.filter(Tire.musteri_id.in_(customer_ids))
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if plate:
            customer = db.query(Customer).filter(Customer.plaka.ilike(f"%{plate}%")).first()
            if customer:
                query = query.filter(Tire.musteri_id == customer.id)
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if customer_phone:
            customers = db.query(Customer).filter(
                Customer.telefon.ilike(f"%{customer_phone}%")
            ).all()
            if customers:
                customer_ids = [c.id for c in customers]
                query = query.filter(Tire.musteri_id.in_(customer_ids))
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if ebat:
            query = query.filter(Tire.ebat.ilike(f"%{ebat}%"))
        
        if brand:
            brand_obj = db.query(Brand).filter(Brand.marka_adi == brand).first()
            if brand_obj:
                query = query.filter(Tire.marka_id == brand_obj.id)
            else:
                query = query.filter(Tire.id == -1)  # No results
        
        if dis_durumu:
            try:
                dis_durum_enum = ModelDisDurumuEnum(dis_durumu)
                query = query.filter(Tire.dis_durumu == dis_durum_enum)
            except (ValueError, AttributeError) as e:
                # Log error but don't fail - just skip this filter
                print(f"Error filtering by dis_durumu: {e}")
                pass
        
        # Status filter is already applied above, no need to apply again here
        
        if entry_date_from:
            try:
                date_from = datetime.fromisoformat(entry_date_from)
                query = query.filter(Tire.giris_tarihi >= date_from)
            except ValueError:
                pass
        
        if entry_date_to:
            try:
                date_to = datetime.fromisoformat(entry_date_to)
                query = query.filter(Tire.giris_tarihi <= date_to)
            except ValueError:
                pass
        
        # Order by entry date descending
        query = query.order_by(Tire.giris_tarihi.desc())
        
        # Get results
        tires = query.all()
        
        # Format tire data for template
        tire_list = []
        for tire in tires:
            tire_list.append({
                "id": tire.id,
                "customer_name": tire.customer.ad_soyad if tire.customer else "",
                "customer_plate": tire.customer.plaka if tire.customer else "",
                "ebat": tire.ebat,
                "brand": tire.brand.marka_adi if tire.brand else "",
                "rack_code": tire.rack.kod if tire.rack else "",
                "giris_tarihi": tire.giris_tarihi,
                "cikis_tarihi": tire.cikis_tarihi,
                "durum": "Depoda" if tire.durum == ModelTireDurumEnum.DEPODA else ("Çıkmış" if tire.durum == ModelTireDurumEnum.CIKTI else (tire.durum.value if hasattr(tire.durum, 'value') else str(tire.durum)))
            })
        
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
            "customer_phone": customer_phone or "",
            "ebat": ebat or "",
            "brand": brand or "",
            "dis_durumu": dis_durumu or "",
            "status": display_status,
            "entry_date_from": entry_date_from or "",
            "entry_date_to": entry_date_to or ""
        }
    
        template = templates.get_template("index.html")
        return HTMLResponse(content=template.render(
            request=request,
            tires=tire_list,
            brands=BRAND_LIST,
            tire_sizes=TIRE_SIZES,
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
async def yeni_lastik(request: Request, db: Session = Depends(get_db)):
    """New tire entry page"""
    # Get only empty racks, ordered by code
    from app.utils.enums import RackDurumEnum
    racks = db.query(Rack).filter(Rack.durum == RackDurumEnum.BOS).order_by(Rack.kod).all()
    rack_list = [{"id": r.id, "kod": r.kod, "durum": r.durum.value if hasattr(r.durum, 'value') else str(r.durum)} for r in racks]
    
    template = templates.get_template("yeni_lastik.html")
    return HTMLResponse(content=template.render(
        request=request,
        brands=BRAND_LIST,
        tire_sizes=TIRE_SIZES,
        racks=rack_list,
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
        query = query.filter(Customer.ad_soyad.ilike(f"%{customer_name}%"))
    
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
        tires = db.query(Tire).filter(Tire.musteri_id == c.id).all()
        
        depoda_count = sum(1 for t in tires if t.durum == ModelTireDurumEnum.DEPODA)
        cikmis_count = sum(1 for t in tires if t.durum == ModelTireDurumEnum.CIKTI)
        
        customer_list.append({
            "id": c.id,
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
    
    template = templates.get_template("raflar.html")
    return HTMLResponse(content=template.render(
        request=request,
        rack_groups=rack_groups_list,
        racks=[],  # Keep for backward compatibility
        current_path="/raflar"
    ))

