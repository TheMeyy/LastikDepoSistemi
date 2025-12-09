from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.models.database import get_db
from app.models.models import Customer
from app.schemas.customer_schema import CustomerCreate, CustomerRead

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""
    existing = db.query(Customer).filter(
        func.lower(Customer.ad_soyad) == func.lower(customer.ad_soyad)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu isimle bir müşteri zaten kayıtlı."
        )
    db_customer = Customer(
        ad_soyad=customer.ad_soyad,
        telefon=customer.telefon,
        plaka=customer.plaka
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.get("/", response_model=List[CustomerRead])
def get_customers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all customers"""
    customers = db.query(Customer).offset(skip).limit(limit).all()
    return customers


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a specific customer by ID"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Update a customer"""
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    # Enforce case-insensitive uniqueness on name (excluding current record)
    existing = db.query(Customer).filter(
        func.lower(Customer.ad_soyad) == func.lower(customer.ad_soyad),
        Customer.id != customer_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu isimle bir müşteri zaten kayıtlı."
        )
    
    db_customer.ad_soyad = customer.ad_soyad
    db_customer.telefon = customer.telefon
    db_customer.plaka = customer.plaka
    
    db.commit()
    db.refresh(db_customer)
    return db_customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer (manually delete related tires to avoid enum issues)"""
    try:
        db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not db_customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Müşteri bulunamadı"
            )
        
        # Get related tires before deletion to update rack statuses
        from app.models.models import Tire, Rack
        from app.utils.enums import RackDurumEnum
        from sqlalchemy import func, cast, String
        
        # Get rack IDs from tires before deletion (avoid enum reading issues)
        # Get rack IDs directly without reading enum to avoid conversion errors
        try:
            # Get rack IDs directly without reading enum
            rack_ids_result = db.query(Tire.raf_id).filter(Tire.musteri_id == customer_id).distinct().all()
            affected_rack_ids = [row[0] for row in rack_ids_result if row[0] is not None]
        except Exception as e:
            print(f"Error getting rack IDs: {e}")
            affected_rack_ids = []
        
        # Delete tires manually first (avoid cascade delete enum issues)
        # Delete tires directly without loading them (to avoid enum reading)
        try:
            # Use bulk delete to avoid loading Tire objects
            deleted_count = db.query(Tire).filter(Tire.musteri_id == customer_id).delete(synchronize_session=False)
            print(f"Deleted {deleted_count} tires for customer {customer_id}")
        except Exception as e:
            print(f"Error deleting tires: {e}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lastikler silinirken bir hata oluştu: {str(e)}"
            )
        
        # Now delete customer
        db.delete(db_customer)
        db.commit()
        
        # Update rack statuses if needed (check if racks are now empty)
        # Use string comparison to avoid enum conversion issues
        for rack_id in affected_rack_ids:
            try:
                rack = db.query(Rack).filter(Rack.id == rack_id).first()
                if rack:
                    # Count remaining tires in this rack with status "DEPODA"
                    # Use cast to string to avoid enum conversion issues
                    remaining_tires_count = db.query(func.count(Tire.id)).filter(
                        Tire.raf_id == rack_id,
                        cast(Tire.durum, String) == "DEPODA"
                    ).scalar()
                    
                    if remaining_tires_count == 0:
                        rack.durum = RackDurumEnum.BOS
                        db.add(rack)
            except Exception as e:
                print(f"Error updating rack {rack_id}: {e}")
                continue  # Continue with next rack
        
        db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Müşteri silinirken bir hata oluştu: {str(e)}"
        )

