from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.models.database import get_db
from app.models.models import Rack
from app.schemas.rack_schema import RackCreate, RackRead
from app.utils.enums import RackDurumEnum

router = APIRouter(prefix="/api/racks", tags=["racks"])


class BulkRackCreate(BaseModel):
    """Schema for bulk creating racks"""
    raf_adi: str = Field(..., description="Rack name prefix (e.g., 'A')")
    sayi: int = Field(..., ge=1, le=100, description="Number of racks to create")


@router.post("/bulk", response_model=List[RackRead], status_code=status.HTTP_201_CREATED)
def create_racks_bulk(bulk_data: BulkRackCreate, db: Session = Depends(get_db)):
    """Create multiple racks at once (e.g., A1, A2, A3... A8)
    
    If racks with the same prefix already exist (e.g., A1-A4), 
    only create missing ones (e.g., A5-A9 if user requests 9).
    If requested number is less than existing racks, show warning.
    """
    try:
        # Find existing racks with the same prefix
        existing_racks = db.query(Rack).filter(
            Rack.kod.like(f"{bulk_data.raf_adi}%")
        ).all()
        
        # Extract existing numbers from rack codes
        existing_numbers = []
        for rack in existing_racks:
            try:
                # Try to extract number from code (e.g., "A4" -> 4)
                code_suffix = rack.kod[len(bulk_data.raf_adi):]
                if code_suffix.isdigit():
                    existing_numbers.append(int(code_suffix))
            except (ValueError, IndexError):
                # If code doesn't match pattern, skip it
                continue
        
        # Find the maximum existing number
        max_existing = max(existing_numbers) if existing_numbers else 0
        
        # Check if requested number is less than existing
        if bulk_data.sayi < max_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bu raf zaten mevcut veya dolu. '{bulk_data.raf_adi}' için en yüksek numara {max_existing}. Lütfen {max_existing + 1} veya daha büyük bir sayı girin."
            )
        
        # Create only missing racks
        created_racks = []
        start_num = max_existing + 1 if existing_numbers else 1
        
        for i in range(start_num, bulk_data.sayi + 1):
            rack_code = f"{bulk_data.raf_adi}{i}"
            
            # Double-check if rack code already exists (safety check)
            existing_rack = db.query(Rack).filter(Rack.kod == rack_code).first()
            if existing_rack:
                # This shouldn't happen, but handle gracefully
                continue
            
            db_rack = Rack(
                kod=rack_code,
                durum=RackDurumEnum.BOS,  # Always start as empty
                not_=None
            )
            db.add(db_rack)
            created_racks.append(db_rack)
        
        # If no new racks to create, inform user
        if not created_racks:
            if existing_numbers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{bulk_data.raf_adi}' için {bulk_data.sayi} adet raf zaten mevcut. En yüksek numara: {max_existing}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Raf oluşturulamadı. Lütfen geçerli bir raf adı ve sayı girin."
                )
        
        db.commit()
        
        # Refresh all created racks
        for rack in created_racks:
            db.refresh(rack)
        
        return created_racks
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Rollback on any unexpected error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Raf oluşturulurken bir hata oluştu: {str(e)}"
        )


@router.post("/", response_model=RackRead, status_code=status.HTTP_201_CREATED)
def create_rack(rack: RackCreate, db: Session = Depends(get_db)):
    """Create a new rack"""
    # Check if rack code already exists
    existing_rack = db.query(Rack).filter(Rack.kod == rack.kod).first()
    if existing_rack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rack with code '{rack.kod}' already exists"
        )
    
    # Always set status to BOS (empty) when creating
    db_rack = Rack(
        kod=rack.kod,
        durum=RackDurumEnum.BOS,  # Always start as empty
        not_=rack.not_
    )
    db.add(db_rack)
    db.commit()
    db.refresh(db_rack)
    return db_rack


@router.get("/", response_model=List[RackRead])
def get_racks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all racks"""
    racks = db.query(Rack).order_by(Rack.kod).offset(skip).limit(limit).all()
    return racks


@router.get("/{rack_id}", response_model=RackRead)
def get_rack(rack_id: int, db: Session = Depends(get_db)):
    """Get a specific rack by ID"""
    rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with ID {rack_id} not found"
        )
    return rack


@router.put("/{rack_id}", response_model=RackRead)
def update_rack(
    rack_id: int,
    rack: RackCreate,
    db: Session = Depends(get_db)
):
    """Update a rack"""
    db_rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not db_rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with ID {rack_id} not found"
        )
    
    # Check if new code conflicts with existing rack
    if rack.kod != db_rack.kod:
        existing_rack = db.query(Rack).filter(Rack.kod == rack.kod).first()
        if existing_rack:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rack with code '{rack.kod}' already exists"
            )
    
    db_rack.kod = rack.kod
    db_rack.durum = rack.durum
    db_rack.not_ = rack.not_
    
    db.commit()
    db.refresh(db_rack)
    return db_rack


@router.delete("/{rack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rack(rack_id: int, db: Session = Depends(get_db)):
    """Delete a rack - only empty racks can be deleted"""
    from app.models.models import Tire
    from app.models.models import TireDurumEnum as ModelTireDurumEnum
    
    db_rack = db.query(Rack).filter(Rack.id == rack_id).first()
    if not db_rack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rack with ID {rack_id} not found"
        )
    
    # Check if rack is empty (no tires with status "Depoda")
    tires_in_rack = db.query(Tire).filter(
        Tire.raf_id == rack_id,
        Tire.durum == ModelTireDurumEnum.DEPODA
    ).count()
    
    if tires_in_rack > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu raf dolu olduğu için silinemez. Önce içindeki lastikleri çıkarın."
        )
    
    # Check if rack status is "Dolu"
    if db_rack.durum == RackDurumEnum.DOLU:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu raf dolu olduğu için silinemez. Önce içindeki lastikleri çıkarın."
        )
    
    db.delete(db_rack)
    db.commit()
    return None

