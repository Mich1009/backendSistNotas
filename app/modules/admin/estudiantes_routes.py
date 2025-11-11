from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from typing import List, Optional
from datetime import datetime

from ...database import get_db
from ..auth.dependencies import get_admin_user
from ..auth.security import get_password_hash
from ...shared.models import User, RoleEnum, Matricula, Nota, Ciclo, Curso, Carrera, DescripcionEvaluacion
from ...shared.grade_calculator import GradeCalculator
from .schemas import UserCreate, UserUpdate, UserResponse, UserListResponse, DescripcionEvaluacionResponse

router = APIRouter(prefix="/estudiantes", tags=["Admin - Estudiantes"])

def get_ciclo_order(ciclo_nombre):
    """Convierte nombres de ciclos a números para ordenamiento"""
    if not ciclo_nombre:
        return 0
    
    # Mapeo de números romanos a enteros
    roman_to_int = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    
    # Extraer el número romano del nombre del ciclo
    ciclo_upper = ciclo_nombre.upper()
    for roman, num in sorted(roman_to_int.items(), key=lambda x: len(x[0]), reverse=True):
        if roman in ciclo_upper:
            return num
    
    return 0

# ==================== CRUD ESTUDIANTES ====================

@router.get("/")
def get_estudiantes(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=1000),
    search: Optional[str] = Query(None),
    ciclo_nombre: Optional[str] = Query(None, description="Filtrar por nombre de ciclo (I, II, III, IV, V, VI)"),
    estado_matricula: Optional[str] = Query(None, regex="^(matriculados|sin_matricular|todos)$", description="Filtrar por estado de matrícula: 'matriculados', 'sin_matricular', 'todos'"),
    db: Session = Depends(get_db)
):
    """Obtener lista de estudiantes activos, mostrando su ciclo más alto si están matriculados"""
    
    # Query base: todos los estudiantes activos ordenados por nombre
    query = db.query(User).options(
        joinedload(User.carrera),
        joinedload(User.estudiante_matriculas).joinedload(Matricula.ciclo)
    ).filter(
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).order_by(User.last_name, User.first_name)
    
    # Aplicar filtros de búsqueda
    if search:
        search_filter = or_(
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
            User.dni.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Obtener todos los estudiantes (sin paginación inicial para procesar ciclos)
    estudiantes = query.all()
    
    # Procesar estudiantes para obtener su ciclo más alto
    estudiantes_procesados = []
    for estudiante in estudiantes:
        # Obtener todas las matrículas activas
        matriculas_activas = [m for m in estudiante.estudiante_matriculas if m.estado == "activa"]
        
        # Crear objeto estudiante base con solo los campos necesarios para el cliente
        estudiante_data = {
            "id": estudiante.id,
            "dni": estudiante.dni,
            "email": estudiante.email,
            "first_name": estudiante.first_name,
            "last_name": estudiante.last_name,
            "phone": estudiante.phone,
            "fecha_nacimiento": estudiante.fecha_nacimiento,
            "direccion": estudiante.direccion,
            "nombre_apoderado": estudiante.nombre_apoderado,
            "telefono_apoderado": estudiante.telefono_apoderado,
            "carrera": {
                "nombre": estudiante.carrera.nombre if estudiante.carrera else None
            } if estudiante.carrera else None,
        }
        
        if matriculas_activas:
            # Encontrar la matrícula con el ciclo más alto usando la función de ordenamiento
            matricula_ciclo_mayor = max(matriculas_activas, key=lambda m: (
                get_ciclo_order(m.ciclo.nombre) if get_ciclo_order(m.ciclo.nombre) > 0 else m.ciclo.numero
            ))
            
            # Agregar solo el ciclo actual que necesita el cliente
            estudiante_data["ciclo_actual"] = matricula_ciclo_mayor.ciclo.nombre
            estudiante_data["ciclo_actual_id"] = matricula_ciclo_mayor.ciclo_id
        else:
            # Estudiante sin matrículas activas
            estudiante_data["ciclo_actual"] = None
            estudiante_data["ciclo_actual_id"] = None
        
        estudiantes_procesados.append(estudiante_data)
    
    # Filtrar por estado de matrícula
    if estado_matricula:
        if estado_matricula == "matriculados":
            estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] is not None]
        elif estado_matricula == "sin_matricular":
            estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] is None]
        # Si es "todos", no filtrar
    
    # Filtrar por ciclo específico si se proporciona
    if ciclo_nombre:
        estudiantes_procesados = [e for e in estudiantes_procesados if e["ciclo_actual"] == ciclo_nombre]
    
    # Aplicar paginación
    total = len(estudiantes_procesados)
    offset = (page - 1) * per_page
    estudiantes_paginados = estudiantes_procesados[offset:offset + per_page]
    total_pages = (total + per_page - 1) // per_page
    
    return {
        "estudiantes": estudiantes_paginados,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_pagination": ciclo_nombre is None  # Indicador para el frontend
    }

@router.post("/", response_model=UserResponse)
def create_estudiante(
    estudiante_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo estudiante"""
    
    # Validar que el rol sea estudiante
    if estudiante_data.role != RoleEnum.ESTUDIANTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol debe ser 'estudiante'"
        )
    
    # Verificar que no exista un usuario con el mismo DNI o email
    existing_user = db.query(User).filter(
        or_(User.dni == estudiante_data.dni, User.email == estudiante_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con ese DNI o email"
        )
    
    # Obtener la carrera por defecto (la primera carrera activa)
    carrera_default = db.query(Carrera).filter(Carrera.is_active == True).first()
    
    if not carrera_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay carreras disponibles en el sistema"
        )
    
    # Crear el estudiante
    hashed_password = get_password_hash(estudiante_data.password)
    
    new_estudiante = User(
        dni=estudiante_data.dni,
        first_name=estudiante_data.first_name,
        last_name=estudiante_data.last_name,
        email=estudiante_data.email,
        hashed_password=hashed_password,
        role=estudiante_data.role,
        phone=estudiante_data.phone,
        fecha_nacimiento=estudiante_data.fecha_nacimiento,
        direccion=estudiante_data.direccion,
        nombre_apoderado=estudiante_data.nombre_apoderado,
        telefono_apoderado=estudiante_data.telefono_apoderado,
        carrera_id=carrera_default.id,  # Asignar carrera por defecto
        is_active=estudiante_data.is_active
    )
    
    db.add(new_estudiante)
    db.commit()
    db.refresh(new_estudiante)
    
    return new_estudiante

@router.put("/{estudiante_id}", response_model=UserResponse)
def update_estudiante(
    estudiante_id: int,
    estudiante_data: UserUpdate,
    db: Session = Depends(get_db)
):
    """Actualizar un estudiante existente"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Verificar email único si se está actualizando
    if estudiante_data.email and estudiante_data.email != estudiante.email:
        existing_user = db.query(User).filter(
            User.email == estudiante_data.email,
            User.id != estudiante_id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con ese email"
            )
    
    # Actualizar campos
    update_data = estudiante_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(estudiante, field, value)
    
    db.commit()
    db.refresh(estudiante)
    
    return estudiante

@router.delete("/{estudiante_id}")
def delete_estudiante(
    estudiante_id: int,
    db: Session = Depends(get_db)
):
    """Eliminar completamente un estudiante (hard delete)"""
    
    estudiante = db.query(User).filter(
        User.id == estudiante_id,
        User.role == RoleEnum.ESTUDIANTE
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado"
        )
    
    # Eliminar completamente el estudiante
    db.delete(estudiante)
    db.commit()
    
    return {"message": "Estudiante eliminado exitosamente"}

@router.get("/search/dni/{dni}")
def search_estudiante_by_dni(
    dni: str,
    db: Session = Depends(get_db)
):
    """Buscar estudiante por DNI para matrícula"""
    
    # Validar formato de DNI
    if not dni or len(dni) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DNI debe tener al menos 8 dígitos"
        )
    
    # Buscar estudiante por DNI
    estudiante = db.query(User).options(
        joinedload(User.carrera)
    ).filter(
        User.dni == dni,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún estudiante con ese DNI"
        )
    
    # Obtener el ciclo actual (matrícula con el ciclo más alto)
    matricula_actual = db.query(Matricula).options(
        joinedload(Matricula.ciclo)
    ).filter(
        Matricula.estudiante_id == estudiante.id,
        Matricula.is_active == True
    ).order_by(Matricula.ciclo_id.desc()).first()
    
    ciclo_actual = matricula_actual.ciclo if matricula_actual else None
    
    return {
        "id": estudiante.id,
        "dni": estudiante.dni,
        "first_name": estudiante.first_name,
        "last_name": estudiante.last_name,
        "email": estudiante.email,
        "phone": estudiante.phone,
        "fecha_nacimiento": estudiante.fecha_nacimiento,
        "direccion": estudiante.direccion,
        "nombre_apoderado": estudiante.nombre_apoderado,
        "telefono_apoderado": estudiante.telefono_apoderado,
        "carrera": {
            "nombre": estudiante.carrera.nombre
        } if estudiante.carrera else None,
        "ciclo_actual": {
            "id": ciclo_actual.id,
            "nombre": ciclo_actual.nombre,
            "numero": ciclo_actual.numero
        } if ciclo_actual else None
    }

@router.get("/{dni}/academic-performance")
def get_academic_performance_by_dni(
    dni: str,
    db: Session = Depends(get_db)
):
    """Obtener el rendimiento académico detallado de un estudiante por DNI"""
    
    # Validar formato de DNI
    if not dni or len(dni) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DNI debe tener al menos 8 dígitos"
        )
    
    # Buscar estudiante por DNI con información de carrera
    estudiante = db.query(User).options(
        joinedload(User.carrera)
    ).filter(
        User.dni == dni,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).first()
    
    if not estudiante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún estudiante con ese DNI"
        )
    
    # Obtener todas las matrículas del estudiante con información del ciclo
    matriculas = db.query(Matricula).options(
        joinedload(Matricula.ciclo)
    ).filter(
        Matricula.estudiante_id == estudiante.id,
        Matricula.is_active == True
    ).all()
    
    if not matriculas:
        return []
    
    performance_data = []
    calculator = GradeCalculator()
    
    for matricula in matriculas:
        # Obtener todos los cursos del ciclo con información del docente
        cursos_ciclo = db.query(Curso).options(
            joinedload(Curso.docente)
        ).filter(
            Curso.ciclo_id == matricula.ciclo_id,
            Curso.is_active == True
        ).all()
        
        # Obtener las notas del estudiante para los cursos de este ciclo
        notas_ciclo = db.query(Nota).options(
            joinedload(Nota.curso)
        ).filter(
            Nota.estudiante_id == estudiante.id,
            Nota.curso_id.in_([curso.id for curso in cursos_ciclo]) if cursos_ciclo else []
        ).all()
        
        # Crear diccionario de notas por curso
        notas_por_curso = {nota.curso_id: nota for nota in notas_ciclo}
        
        # Procesar cada curso del ciclo
        cursos_rendimiento = []
        
        for curso in cursos_ciclo:
            nota = notas_por_curso.get(curso.id)
            
            if nota:
                # Calcular promedio final
                try:
                    promedio_final = calculator.calcular_promedio_nota(nota)
                except Exception as e:
                    promedio_final = None
                
                # Preparar evaluaciones
                evaluaciones = {}
                for i in range(1, 9):
                    eval_val = getattr(nota, f'evaluacion{i}')
                    evaluaciones[f'evaluacion{i}'] = float(eval_val) if eval_val is not None else None
                
                # Preparar prácticas
                practicas = {}
                for i in range(1, 5):
                    prac_val = getattr(nota, f'practica{i}')
                    practicas[f'practica{i}'] = float(prac_val) if prac_val is not None else None
                
                # Preparar parciales
                parciales = {}
                for i in range(1, 3):
                    parc_val = getattr(nota, f'parcial{i}')
                    parciales[f'parcial{i}'] = float(parc_val) if parc_val is not None else None
                
                # Determinar estado basado en las notas completadas
                if promedio_final and float(promedio_final) >= 13.0:
                    estado = "Aprobado"
                elif promedio_final and float(promedio_final) < 13.0:
                    estado = "Desaprobado"
                else:
                    # Verificar si tiene algunas notas (en curso) o ninguna (pendiente)
                    tiene_notas = any([
                        any(evaluaciones.values()),
                        any(practicas.values()),
                        any(parciales.values())
                    ])
                    estado = "En curso" if tiene_notas else "Pendiente"
            
            else:
                # Curso sin notas
                promedio_final = None
                evaluaciones = {f'evaluacion{i}': None for i in range(1, 9)}
                practicas = {f'practica{i}': None for i in range(1, 5)}
                parciales = {f'parcial{i}': None for i in range(1, 3)}
                estado = "Pendiente"
            
            curso_rendimiento = {
                "curso_id": curso.id,
                "curso_nombre": curso.nombre,
                "promedio_final": float(promedio_final) if promedio_final else None,
                "estado": estado,
                "evaluaciones": evaluaciones,
                "practicas": practicas,
                "parciales": parciales
            }
            
            cursos_rendimiento.append(curso_rendimiento)
        
        # Calcular estadísticas del ciclo
        numero_cursos = len(cursos_rendimiento)
        
        # Calcular promedio del ciclo (solo cursos con promedio final)
        promedios_validos = [curso["promedio_final"] for curso in cursos_rendimiento if curso["promedio_final"] is not None]
        promedio_ciclo = sum(promedios_validos) / len(promedios_validos) if promedios_validos else None
        
        # Crear el objeto de datos de rendimiento del ciclo
        ciclo_data = {
            "ciclo_id": matricula.ciclo.id,
            "ciclo_nombre": matricula.ciclo.nombre,
            "ciclo_numero": matricula.ciclo.numero,
            "numero_cursos": numero_cursos,
            "promedio_ciclo": round(promedio_ciclo, 2) if promedio_ciclo else None,
            "ciclo_info": {
                "id": matricula.ciclo.id,
                "nombre": matricula.ciclo.nombre,
                "numero": matricula.ciclo.numero
            },
            "cursos": cursos_rendimiento
        }
        
        performance_data.append(ciclo_data)
    
    # Ordenar por número de ciclo
    performance_data.sort(key=lambda x: x["ciclo_info"]["numero"])
    
    return {
        "estudiante": {
            "id": estudiante.id,
            "dni": estudiante.dni,
            "first_name": estudiante.first_name,
            "last_name": estudiante.last_name,
            "email": estudiante.email,
            "carrera": estudiante.carrera.nombre if estudiante.carrera else None
        },
        "academic_performance": performance_data
    }
    
    
# ==================== DESCRIPCIONES DE EVALUACIÓN ====================

@router.get("/nota/{curso_id}/evaluation-descriptions", response_model=List[DescripcionEvaluacionResponse])
def get_evaluation_descriptions(
    curso_id: int,
    db: Session = Depends(get_db)
):
    """Obtener todas las descripciones de evaluación de un curso"""
    
    # Verificar que el curso existe
    curso = db.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado"
        )
    
    # Obtener todas las descripciones de evaluación del curso
    descripciones = db.query(DescripcionEvaluacion).filter(
        DescripcionEvaluacion.curso_id == curso_id
    ).all()
    
    return descripciones