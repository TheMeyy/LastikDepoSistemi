from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    """Schema for creating a customer"""
    ad_soyad: str = Field(..., description="Customer full name")
    telefon: str = Field(..., description="Customer phone number")
    plaka: str = Field(..., description="Customer license plate")

    class Config:
        json_schema_extra = {
            "example": {
                "ad_soyad": "Ahmet Yılmaz",
                "telefon": "05551234567",
                "plaka": "34ABC123"
            }
        }


class CustomerRead(BaseModel):
    """Schema for reading a customer"""
    id: int
    ad_soyad: str
    telefon: str
    plaka: str

    class Config:
        from_attributes = True







