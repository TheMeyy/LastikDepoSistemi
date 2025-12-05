from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.utils.enums import MevsimEnum, DisDurumuEnum, TireDurumEnum, BRAND_LIST


class TireCreate(BaseModel):
    """Schema for creating a tire"""
    musteri_id: int = Field(..., description="Customer ID")
    brand: str = Field(..., description="Tire brand")
    ebat: Optional[str] = Field(None, description="Tire size (deprecated, use tire1_size-tire6_size)")
    mevsim: MevsimEnum = Field(..., description="Season")
    dis_durumu: DisDurumuEnum = Field(..., description="Tire condition")
    not_: Optional[str] = Field(None, alias="not", description="Optional note")
    raf_id: int = Field(..., description="Rack ID")
    giris_tarihi: Optional[datetime] = Field(None, description="Entry date (defaults to now)")
    cikis_tarihi: Optional[datetime] = Field(None, description="Exit date")
    durum: TireDurumEnum = Field(default=TireDurumEnum.DEPODA, description="Tire status")
    
    # Multiple tire support (up to 6 tires)
    tire1_size: Optional[str] = Field(None, description="Tire 1 size")
    tire1_production_date: Optional[str] = Field(None, description="Tire 1 production year (e.g., '2024')")
    tire2_size: Optional[str] = Field(None, description="Tire 2 size")
    tire2_production_date: Optional[str] = Field(None, description="Tire 2 production year (e.g., '2024')")
    tire3_size: Optional[str] = Field(None, description="Tire 3 size")
    tire3_production_date: Optional[str] = Field(None, description="Tire 3 production year (e.g., '2024')")
    tire4_size: Optional[str] = Field(None, description="Tire 4 size")
    tire4_production_date: Optional[str] = Field(None, description="Tire 4 production year (e.g., '2024')")
    tire5_size: Optional[str] = Field(None, description="Tire 5 size")
    tire5_production_date: Optional[str] = Field(None, description="Tire 5 production year (e.g., '2024')")
    tire6_size: Optional[str] = Field(None, description="Tire 6 size")
    tire6_production_date: Optional[str] = Field(None, description="Tire 6 production year (e.g., '2024')")
    
    @field_validator("durum", mode="before")
    @classmethod
    def validate_durum(cls, v):
        if v is None:
            return TireDurumEnum.DEPODA
        if isinstance(v, str):
            # Convert string to enum
            v_clean = v.strip()
            if v_clean == "Çıkmış" or v_clean == "CIKTI":
                return TireDurumEnum.CIKTI
            elif v_clean == "Depoda" or v_clean == "DEPODA":
                return TireDurumEnum.DEPODA
            else:
                # Try to convert directly using enum value
                try:
                    # Try by value first
                    for enum_item in TireDurumEnum:
                        if enum_item.value == v_clean:
                            return enum_item
                    # If not found, try by name
                    return TireDurumEnum[v_clean]
                except (ValueError, KeyError):
                    raise ValueError(f"Invalid tire status: '{v}'. Must be 'Depoda', 'Çıkmış', 'DEPODA', or 'CIKTI'")
        elif isinstance(v, TireDurumEnum):
            return v
        return v

    # Brand validation removed - brands are now stored in database and can be added dynamically

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "musteri_id": 1,
                "brand": "Michelin",
                "ebat": "205/55 R16",
                "mevsim": "Yaz",
                "dis_durumu": "İyi",
                "not": "Yeni lastik",
                "raf_id": 1,
                "durum": "Depoda"
            }
        }


class TireRead(BaseModel):
    """Schema for reading a tire"""
    id: int
    seri_no: int  # Otomatik artan seri numarası
    musteri_id: int
    brand: str  # Will be populated from Brand relationship
    ebat: str
    mevsim: MevsimEnum
    dis_durumu: DisDurumuEnum
    not_: Optional[str] = Field(None, alias="not")
    raf_id: int
    rack_code: str  # Will be populated from Rack relationship
    giris_tarihi: datetime
    cikis_tarihi: Optional[datetime]
    durum: TireDurumEnum
    customer_name: str  # Will be populated from Customer relationship
    customer_plate: str  # Will be populated from Customer relationship
    
    # Multiple tire support (up to 6 tires)
    tire1_size: Optional[str] = None
    tire1_production_date: Optional[str] = None  # Year as string (e.g., "2024")
    tire2_size: Optional[str] = None
    tire2_production_date: Optional[str] = None  # Year as string (e.g., "2024")
    tire3_size: Optional[str] = None
    tire3_production_date: Optional[str] = None  # Year as string (e.g., "2024")
    tire4_size: Optional[str] = None
    tire4_production_date: Optional[str] = None  # Year as string (e.g., "2024")
    tire5_size: Optional[str] = None
    tire5_production_date: Optional[str] = None  # Year as string (e.g., "2024")
    tire6_size: Optional[str] = None
    tire6_production_date: Optional[str] = None  # Year as string (e.g., "2024")

    class Config:
        from_attributes = True
        populate_by_name = True

