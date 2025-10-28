from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import pandas as pd
import io
import json

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ...shared.models import User, RoleEnum, Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota
from ...shared.grade_utils import calcular_promedio_nota, obtener_notas_con_promedio
from .schemas import (
    ReporteUsuarios, ReporteAcademico, EstadisticasGenerales
)

router = APIRouter(prefix="/reportes", tags=["Admin - Reportes"])

# ==================== VISTA DE REPORTES DINAMICOS ====================
