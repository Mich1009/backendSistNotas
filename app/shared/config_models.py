"""
Modelos para configuraciones del sistema
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..database import Base

class SiteConfig(Base):
    __tablename__ = "site_config"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    value = Column(String(10000), nullable=False)  # Aumentado de 255 a 10000 para soportar imágenes en base64
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SiteConfig(key={self.key}, value={self.value})>"