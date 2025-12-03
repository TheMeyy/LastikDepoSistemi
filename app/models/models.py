from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base


# Enum classes
class MevsimEnum(str, enum.Enum):
    YAZ = "Yaz"
    KIS = "Kış"
    DORT_MEVSIM = "4 Mevsim"


class DisDurumuEnum(str, enum.Enum):
    SIFIR = "Sıfır"
    IYI = "İyi"
    ORTA = "Orta"
    KOTU = "Kötü"


class TireDurumEnum(str, enum.Enum):
    DEPODA = "DEPODA"
    CIKTI = "CIKTI"


class RackDurumEnum(str, enum.Enum):
    BOS = "Boş"
    DOLU = "Dolu"


# Database Models
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    ad_soyad = Column(String, nullable=False)
    telefon = Column(String, nullable=False)
    plaka = Column(String, nullable=False)

    # Relationship: one customer can have multiple tires (cascade delete)
    tires = relationship("Tire", back_populates="customer", cascade="all, delete-orphan")


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    marka_adi = Column(String, nullable=False, unique=True)

    # Relationship: one brand can have multiple tires
    tires = relationship("Tire", back_populates="brand")


class TireSize(Base):
    __tablename__ = "tire_sizes"

    id = Column(Integer, primary_key=True, index=True)
    ebat = Column(String, nullable=False, unique=True)


class Rack(Base):
    __tablename__ = "racks"

    id = Column(Integer, primary_key=True, index=True)
    kod = Column(String, nullable=False, unique=True)
    durum = Column(Enum(RackDurumEnum), nullable=False, default=RackDurumEnum.BOS)
    not_ = Column("not", Text, nullable=True)

    # Relationship: one rack can store multiple tires
    tires = relationship("Tire", back_populates="rack")


class Tire(Base):
    __tablename__ = "tires"

    id = Column(Integer, primary_key=True, index=True)
    musteri_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    marka_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    ebat = Column(String, nullable=False)  # Deprecated: kept for backward compatibility
    mevsim = Column(Enum(MevsimEnum), nullable=False)
    dis_durumu = Column(Enum(DisDurumuEnum), nullable=False)
    not_ = Column("not", Text, nullable=True)
    raf_id = Column(Integer, ForeignKey("racks.id"), nullable=False)
    giris_tarihi = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    cikis_tarihi = Column(DateTime(timezone=True), nullable=True)
    durum = Column(Enum(TireDurumEnum, native_enum=False, length=20), nullable=False, default=TireDurumEnum.DEPODA)
    
    # Multiple tire support (up to 6 tires)
    tire1_size = Column(String, nullable=True)
    tire1_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")
    tire2_size = Column(String, nullable=True)
    tire2_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")
    tire3_size = Column(String, nullable=True)
    tire3_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")
    tire4_size = Column(String, nullable=True)
    tire4_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")
    tire5_size = Column(String, nullable=True)
    tire5_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")
    tire6_size = Column(String, nullable=True)
    tire6_production_date = Column(String, nullable=True)  # Year as string (e.g., "2024")

    # Relationships
    customer = relationship("Customer", back_populates="tires")
    brand = relationship("Brand", back_populates="tires")
    rack = relationship("Rack", back_populates="tires")

