from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from datetime import datetime
from app.models.database import get_db
from app.models.models import Tire, Brand, Customer, Rack
from app.models.models import TireDurumEnum as ModelTireDurumEnum
from app.schemas.tire_schema import TireCreate, TireRead
from app.utils.enums import TireDurumEnum, MevsimEnum, DisDurumuEnum, BRAND_LIST, RackDurumEnum

router = APIRouter(prefix="/api/tires", tags=["tires"])


def get_or_create_brand(db: Session, brand_name: str) -> Brand:
    """Get existing brand or create if it doesn't exist"""
    brand = db.query(Brand).filter(Brand.marka_adi == brand_name).first()
    if not brand:
        brand = Brand(marka_adi=brand_name)
        db.add(brand)
        db.commit()
        db.refresh(brand)
    return brand


@router.post("/", response_model=TireRead, status_code=status.HTTP_201_CREATED)
def create_tire(tire: TireCreate, db: Session = Depends(get_db)):
    """Create a new tire"""
    # Validate customer exists
    customer = db.query(Customer).filter(Customer.id == tire.musteri_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {tire.musteri_id} not found"
        )
    
    # Validate rack exists
    rack = db.query(Rack).filter(Rack.id == tire.raf_id).first()
    if not rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with ID {tire.raf_id} not found"
        )
    
    # Get or create brand
    brand = get_or_create_brand(db, tire.brand)
    
    # Set entry date if not provided
    entry_date = tire.giris_tarihi if tire.giris_tarihi else datetime.now()
    
    # Convert durum enum from schema enum to model enum
    # Schema uses TireDurumEnum from utils.enums (values: "Depoda", "Çıkmış")
    # Model uses TireDurumEnum from models.models (values: "DEPODA", "CIKTI")
    # ModelTireDurumEnum is already imported at the top
    if isinstance(tire.durum, str):
        if tire.durum.strip() == "Depoda" or tire.durum.strip() == "DEPODA":
            durum_value = ModelTireDurumEnum.DEPODA
        elif tire.durum.strip() == "Çıkmış" or tire.durum.strip() == "CIKTI":
            durum_value = ModelTireDurumEnum.CIKTI
        else:
            durum_value = ModelTireDurumEnum.DEPODA  # Default
    else:
        # It's an enum instance from schema
        # Check its value and convert to model enum
        durum_str = tire.durum.value if hasattr(tire.durum, 'value') else str(tire.durum)
        if durum_str == "Depoda" or durum_str == "DEPODA":
            durum_value = ModelTireDurumEnum.DEPODA
        elif durum_str == "Çıkmış" or durum_str == "CIKTI":
            durum_value = ModelTireDurumEnum.CIKTI
        else:
            durum_value = ModelTireDurumEnum.DEPODA  # Default
    
    try:
        db_tire = Tire(
            musteri_id=tire.musteri_id,
            marka_id=brand.id,
            ebat=tire.ebat or '',
            mevsim=tire.mevsim,
            dis_durumu=tire.dis_durumu,
            not_=tire.not_,
            raf_id=tire.raf_id,
            giris_tarihi=entry_date,
            cikis_tarihi=tire.cikis_tarihi,
            durum=durum_value,
            # Multiple tire support
            tire1_size=tire.tire1_size,
            tire1_production_date=tire.tire1_production_date,
            tire2_size=tire.tire2_size,
            tire2_production_date=tire.tire2_production_date,
            tire3_size=tire.tire3_size,
            tire3_production_date=tire.tire3_production_date,
            tire4_size=tire.tire4_size,
            tire4_production_date=tire.tire4_production_date,
            tire5_size=tire.tire5_size,
            tire5_production_date=tire.tire5_production_date,
            tire6_size=tire.tire6_size,
            tire6_production_date=tire.tire6_production_date
        )
        db.add(db_tire)
        
        # Update rack status to "Dolu" (Full)
        rack.durum = RackDurumEnum.DOLU
        db.add(rack)
        
        # Commit both changes together (atomic transaction)
        db.commit()
        db.refresh(db_tire)
        
        # Reload with relationships
        from sqlalchemy.orm import joinedload
        db_tire = db.query(Tire).options(
            joinedload(Tire.brand),
            joinedload(Tire.customer),
            joinedload(Tire.rack)
        ).filter(Tire.id == db_tire.id).first()
        
        # Return with relationships loaded
        return format_tire_response(db_tire, db)
    except Exception as e:
        # Rollback on any error to ensure data consistency
        db.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error creating tire: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lastik eklenirken bir hata oluştu: {str(e)}"
        )


@router.get("/", response_model=List[TireRead])
def get_tires(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    brand: Optional[str] = Query(None, description="Filter by brand name"),
    status: Optional[TireDurumEnum] = Query(None, description="Filter by status"),
    plate: Optional[str] = Query(None, description="Filter by customer license plate"),
    rack_code: Optional[str] = Query(None, description="Filter by rack code"),
    entry_date_from: Optional[datetime] = Query(None, description="Filter by entry date from"),
    entry_date_to: Optional[datetime] = Query(None, description="Filter by entry date to"),
    exit_date_from: Optional[datetime] = Query(None, description="Filter by exit date from"),
    exit_date_to: Optional[datetime] = Query(None, description="Filter by exit date to"),
    db: Session = Depends(get_db)
):
    """Get all tires with optional filtering"""
    query = db.query(Tire)
    
    # Apply filters
    if brand:
        brand_obj = db.query(Brand).filter(Brand.marka_adi == brand).first()
        if brand_obj:
            query = query.filter(Tire.marka_id == brand_obj.id)
        else:
            # Brand doesn't exist, return empty list
            return []
    
    if status:
        query = query.filter(Tire.durum == status)
    
    if plate:
        customer = db.query(Customer).filter(Customer.plaka == plate).first()
        if customer:
            query = query.filter(Tire.musteri_id == customer.id)
        else:
            # Customer with this plate doesn't exist
            return []
    
    if rack_code:
        rack = db.query(Rack).filter(Rack.kod == rack_code).first()
        if rack:
            query = query.filter(Tire.raf_id == rack.id)
        else:
            # Rack with this code doesn't exist
            return []
    
    if entry_date_from:
        query = query.filter(Tire.giris_tarihi >= entry_date_from)
    
    if entry_date_to:
        query = query.filter(Tire.giris_tarihi <= entry_date_to)
    
    if exit_date_from:
        query = query.filter(Tire.cikis_tarihi >= exit_date_from)
    
    if exit_date_to:
        query = query.filter(Tire.cikis_tarihi <= exit_date_to)
    
    # Order by entry_date descending
    query = query.order_by(Tire.giris_tarihi.desc())
    
    # Apply pagination and eager load relationships
    from sqlalchemy.orm import joinedload
    tires = query.options(
        joinedload(Tire.brand),
        joinedload(Tire.customer),
        joinedload(Tire.rack)
    ).offset(skip).limit(limit).all()
    
    # Format response with relationships
    return [format_tire_response(tire, db) for tire in tires]


@router.get("/{tire_id}", response_model=TireRead)
def get_tire(tire_id: int, db: Session = Depends(get_db)):
    """Get a specific tire by ID"""
    try:
        from sqlalchemy.orm import joinedload
        tire = db.query(Tire).options(
            joinedload(Tire.brand),
            joinedload(Tire.customer),
            joinedload(Tire.rack)
        ).filter(Tire.id == tire_id).first()
        if not tire:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tire with ID {tire_id} not found"
            )
        return format_tire_response(tire, db)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_tire endpoint: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tire: {str(e)}"
        )


@router.put("/{tire_id}", response_model=TireRead)
def update_tire(
    tire_id: int,
    tire: TireCreate,
    db: Session = Depends(get_db)
):
    """Update a tire"""
    try:
        db_tire = db.query(Tire).filter(Tire.id == tire_id).first()
        if not db_tire:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tire with ID {tire_id} not found"
            )
        
        # Validate customer exists
        customer = db.query(Customer).filter(Customer.id == tire.musteri_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {tire.musteri_id} not found"
            )
        
        # Validate rack exists
        rack = db.query(Rack).filter(Rack.id == tire.raf_id).first()
        if not rack:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rack with ID {tire.raf_id} not found"
            )
        
        # Get or create brand
        brand = get_or_create_brand(db, tire.brand)
        
        # Store old rack ID to update its status if changed
        old_rack_id = db_tire.raf_id
        old_rack = db.query(Rack).filter(Rack.id == old_rack_id).first()
        
        # Update tire fields
        db_tire.musteri_id = tire.musteri_id
        db_tire.marka_id = brand.id
        db_tire.ebat = tire.ebat or ''
        db_tire.mevsim = tire.mevsim
        db_tire.dis_durumu = tire.dis_durumu
        db_tire.not_ = tire.not_
        db_tire.raf_id = tire.raf_id
        if tire.giris_tarihi:
            db_tire.giris_tarihi = tire.giris_tarihi
        db_tire.cikis_tarihi = tire.cikis_tarihi
        
        # Update multiple tire fields
        db_tire.tire1_size = tire.tire1_size
        db_tire.tire1_production_date = tire.tire1_production_date
        db_tire.tire2_size = tire.tire2_size
        db_tire.tire2_production_date = tire.tire2_production_date
        db_tire.tire3_size = tire.tire3_size
        db_tire.tire3_production_date = tire.tire3_production_date
        db_tire.tire4_size = tire.tire4_size
        db_tire.tire4_production_date = tire.tire4_production_date
        db_tire.tire5_size = tire.tire5_size
        db_tire.tire5_production_date = tire.tire5_production_date
        db_tire.tire6_size = tire.tire6_size
        db_tire.tire6_production_date = tire.tire6_production_date
        
        # Ensure durum is enum, not string
        # Convert from utils enum to model enum (they should match now, but be safe)
        if isinstance(tire.durum, str):
            if tire.durum.strip() == "Çıkmış":
                db_tire.durum = ModelTireDurumEnum.CIKTI
            elif tire.durum.strip() == "Depoda":
                db_tire.durum = ModelTireDurumEnum.DEPODA
            else:
                # Try to find enum by value
                found = None
                for enum_val in ModelTireDurumEnum:
                    if enum_val.value == tire.durum.strip():
                        found = enum_val
                        break
                if found:
                    db_tire.durum = found
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid tire status: '{tire.durum}'. Must be 'Depoda' or 'Çıkmış'"
                    )
        elif isinstance(tire.durum, TireDurumEnum):
            # Convert from utils enum to model enum
            if tire.durum == TireDurumEnum.CIKTI:
                db_tire.durum = ModelTireDurumEnum.CIKTI
            elif tire.durum == TireDurumEnum.DEPODA:
                db_tire.durum = ModelTireDurumEnum.DEPODA
            else:
                db_tire.durum = ModelTireDurumEnum(tire.durum.value)
        elif isinstance(tire.durum, ModelTireDurumEnum):
            # Already model enum, use directly
            db_tire.durum = tire.durum
        else:
            # Try to convert
            try:
                if hasattr(tire.durum, 'value'):
                    # It's an enum-like object
                    db_tire.durum = ModelTireDurumEnum(tire.durum.value)
                else:
                    db_tire.durum = ModelTireDurumEnum(str(tire.durum))
            except (ValueError, AttributeError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tire status format: {type(tire.durum)}, value: {tire.durum}, error: {str(e)}"
                )
        
        # Final check: ensure durum is model enum instance
        if not isinstance(db_tire.durum, ModelTireDurumEnum):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to convert tire status to enum. Got: {type(db_tire.durum)}, value: {db_tire.durum}"
            )
        
        # Update rack statuses based on tire status
        # If tire is "Çıkmış" (Exited), set rack to "Boş" (Empty)
        # Use model enum for comparison
        if db_tire.durum == ModelTireDurumEnum.CIKTI:
            if old_rack:
                # Check if there are other tires in this rack
                from sqlalchemy import func
                other_tires_count = db.query(func.count(Tire.id)).filter(
                    Tire.raf_id == old_rack_id,
                    Tire.id != tire_id,
                    Tire.durum == ModelTireDurumEnum.DEPODA
                ).scalar()
                if other_tires_count == 0:
                    old_rack.durum = RackDurumEnum.BOS
                    db.add(old_rack)
        elif db_tire.durum == ModelTireDurumEnum.DEPODA:
            # If tire is "Depoda" (In Depot), set rack to "Dolu" (Full)
            rack.durum = RackDurumEnum.DOLU
            db.add(rack)
            # If rack changed, set old rack to empty if no other tires
            if old_rack_id != tire.raf_id and old_rack:
                from sqlalchemy import func
                other_tires_count = db.query(func.count(Tire.id)).filter(
                    Tire.raf_id == old_rack_id,
                    Tire.id != tire_id,
                    Tire.durum == ModelTireDurumEnum.DEPODA
                ).scalar()
                if other_tires_count == 0:
                    old_rack.durum = RackDurumEnum.BOS
                    db.add(old_rack)
        
        db.commit()
        db.refresh(db_tire)
        
        # Reload with relationships
        from sqlalchemy.orm import joinedload
        db_tire = db.query(Tire).options(
            joinedload(Tire.brand),
            joinedload(Tire.customer),
            joinedload(Tire.rack)
        ).filter(Tire.id == db_tire.id).first()
        
        return format_tire_response(db_tire, db)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tire: {str(e)}"
        )


@router.delete("/{tire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tire(tire_id: int, db: Session = Depends(get_db)):
    """Delete a tire"""
    db_tire = db.query(Tire).filter(Tire.id == tire_id).first()
    if not db_tire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tire with ID {tire_id} not found"
        )
    
    rack_id = db_tire.raf_id
    
    db.delete(db_tire)
    
    # Check if there are other tires in this rack
    from sqlalchemy import func
    other_tires_count = db.query(func.count(Tire.id)).filter(
        Tire.raf_id == rack_id,
        Tire.durum == TireDurumEnum.DEPODA
    ).scalar()
    
    # If no other tires in rack, set rack status to "Boş"
    if other_tires_count == 0:
        rack = db.query(Rack).filter(Rack.id == rack_id).first()
        if rack:
            rack.durum = RackDurumEnum.BOS
            db.add(rack)
    
    db.commit()
    return None


def format_tire_response(tire: Tire, db: Session) -> TireRead:
    """Format tire response with relationships"""
    try:
        # Load relationships using SQLAlchemy relationships (more efficient)
        brand_name = tire.brand.marka_adi if tire.brand else ""
        customer_name = tire.customer.ad_soyad if tire.customer else ""
        customer_plate = tire.customer.plaka if tire.customer else ""
        rack_code = tire.rack.kod if tire.rack else ""
        
        # Ensure durum is enum instance - convert from ModelTireDurumEnum to TireDurumEnum (utils)
        from app.utils.enums import TireDurumEnum as UtilsTireDurumEnum
        
        durum_value = tire.durum
        if isinstance(tire.durum, ModelTireDurumEnum):
            # Convert from ModelTireDurumEnum to UtilsTireDurumEnum
            if tire.durum == ModelTireDurumEnum.DEPODA:
                durum_value = UtilsTireDurumEnum.DEPODA
            elif tire.durum == ModelTireDurumEnum.CIKTI:
                durum_value = UtilsTireDurumEnum.CIKTI
            else:
                durum_value = UtilsTireDurumEnum.DEPODA  # Default
        elif isinstance(tire.durum, str):
            # Convert string to enum
            if tire.durum == "DEPODA" or tire.durum == "Depoda":
                durum_value = UtilsTireDurumEnum.DEPODA
            elif tire.durum == "CIKTI" or tire.durum == "Çıkmış":
                durum_value = UtilsTireDurumEnum.CIKTI
            else:
                # Try to find by value
                for enum_val in UtilsTireDurumEnum:
                    if enum_val.value == tire.durum:
                        durum_value = enum_val
                        break
                else:
                    durum_value = UtilsTireDurumEnum.DEPODA  # Default
        elif hasattr(tire.durum, 'value'):
            # It's an enum-like object
            try:
                durum_str = tire.durum.value if hasattr(tire.durum, 'value') else str(tire.durum)
                if durum_str == "DEPODA" or durum_str == "Depoda":
                    durum_value = UtilsTireDurumEnum.DEPODA
                elif durum_str == "CIKTI" or durum_str == "Çıkmış":
                    durum_value = UtilsTireDurumEnum.CIKTI
                else:
                    durum_value = UtilsTireDurumEnum(durum_str)
            except (ValueError, AttributeError):
                durum_value = UtilsTireDurumEnum.DEPODA  # Default
        else:
            durum_value = UtilsTireDurumEnum.DEPODA  # Default
        
        return TireRead(
            id=tire.id,
            musteri_id=tire.musteri_id,
            brand=brand_name,
            ebat=tire.ebat,
            mevsim=tire.mevsim,
            dis_durumu=tire.dis_durumu,
            not_=tire.not_,
            raf_id=tire.raf_id,
            rack_code=rack_code,
            giris_tarihi=tire.giris_tarihi,
            cikis_tarihi=tire.cikis_tarihi,
            durum=durum_value,
            customer_name=customer_name,
            customer_plate=customer_plate,
            # Multiple tire support
            tire1_size=tire.tire1_size,
            tire1_production_date=tire.tire1_production_date,
            tire2_size=tire.tire2_size,
            tire2_production_date=tire.tire2_production_date,
            tire3_size=tire.tire3_size,
            tire3_production_date=tire.tire3_production_date,
            tire4_size=tire.tire4_size,
            tire4_production_date=tire.tire4_production_date,
            tire5_size=tire.tire5_size,
            tire5_production_date=tire.tire5_production_date,
            tire6_size=tire.tire6_size,
            tire6_production_date=tire.tire6_production_date
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in format_tire_response: {error_trace}")
        print(f"Tire durum type: {type(tire.durum)}, value: {tire.durum}")
        raise

