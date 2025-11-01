#!/usr/bin/env python3
"""
Seeder para configuraciones del sistema
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.shared.config_models import SiteConfig

def create_site_configs():
    """Crea las configuraciones básicas del sistema"""
    db: Session = SessionLocal()
    
    try:
        # Configuración del logo de login
        login_logo = db.query(SiteConfig).filter(SiteConfig.key == "login_logo").first()
        if not login_logo:
            login_logo = SiteConfig(
                key="login_logo",
                value="/static/uploads/default-logo.png",
                description="Logo mostrado en la página de login"
            )
            db.add(login_logo)
            db.commit()
            db.refresh(login_logo)
            print("Configuración de logo creada correctamente")
        else:
            print("Configuración de logo ya existe")
        
        # Aquí puedes agregar más configuraciones del sistema
        
        return True
    except Exception as e:
        db.rollback()
        print(f"Error al crear configuraciones: {str(e)}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    create_site_configs()
    print("Seeder de configuraciones completado")