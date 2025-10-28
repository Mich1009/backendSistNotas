from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import pandas as pd
import io

from ...database import get_db
from ..auth.dependencies import get_docente_user
from ..auth.models import User, RoleEnum
from .models import Carrera, Ciclo, Curso, Matricula, Nota, HistorialNota, DescripcionEvaluacion
from app.shared import email_service
from ...shared.grade_calculator import GradeCalculator
from .schemas import (
    NotaCreate, NotaUpdate, NotaDocenteResponse, ActualizacionMasivaNotas,
    NotaResponse, PromedioFinalResponse, EstructuraNotasResponse, NotaMasivaCreate,
    ConfiguracionCalculoNotas, HistorialNotaResponse, NotasFilter,
    NotasPaginationResponse
)

router = APIRouter()

@router.get("/courses/{curso_id}/grades", response_model=List[NotaResponse])
def get_course_grades(
    curso_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_docente_user),
    estudiante_id: Optional[int] = Query(None)
):
    """
    Obtener todas las notas de un curso - ahora un solo registro por estudiante
    """
    # Verificar que el curso exista y pertenezca al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id
    ).first()

    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no pertenece al docente"
        )

    # Construir query base - ahora solo un registro por estudiante
    query = db.query(Nota).join(User, User.id == Nota.estudiante_id).filter(
        Nota.curso_id == curso_id
    )

    # Aplicar filtro de estudiante si se especifica
    if estudiante_id:
        query = query.filter(Nota.estudiante_id == estudiante_id)

    notas = query.order_by(User.last_name, User.first_name).all()

    # Formatear respuesta
    notas_data = []
    for nota in notas:
        estudiante = nota.estudiante
        notas_data.append(NotaResponse(
            id=nota.id,
            estudiante_id=estudiante.id,
            estudiante_nombre=f"{estudiante.first_name} {estudiante.last_name}",
            curso_id=nota.curso_id,
            
            # Campos de evaluaciones
            evaluacion1=float(nota.evaluacion1) if nota.evaluacion1 else None,
            evaluacion2=float(nota.evaluacion2) if nota.evaluacion2 else None,
            evaluacion3=float(nota.evaluacion3) if nota.evaluacion3 else None,
            evaluacion4=float(nota.evaluacion4) if nota.evaluacion4 else None,
            evaluacion5=float(nota.evaluacion5) if nota.evaluacion5 else None,
            evaluacion6=float(nota.evaluacion6) if nota.evaluacion6 else None,
            evaluacion7=float(nota.evaluacion7) if nota.evaluacion7 else None,
            evaluacion8=float(nota.evaluacion8) if nota.evaluacion8 else None,
            
            # Campos de prácticas
            practica1=float(nota.practica1) if nota.practica1 else None,
            practica2=float(nota.practica2) if nota.practica2 else None,
            practica3=float(nota.practica3) if nota.practica3 else None,
            practica4=float(nota.practica4) if nota.practica4 else None,
            
            # Campos de parciales
            parcial1=float(nota.parcial1) if nota.parcial1 else None,
            parcial2=float(nota.parcial2) if nota.parcial2 else None,
            
            # Resultados calculados
            promedio_evaluaciones=GradeCalculator.calcular_promedio_evaluaciones(nota),
            promedio_practicas=GradeCalculator.calcular_promedio_practicas(nota),
            promedio_parciales=GradeCalculator.calcular_promedio_parciales(nota),
            promedio_final=nota.calcular_promedio_final(),
            estado=nota.obtener_estado(),
            
            fecha_registro=nota.fecha_registro.isoformat(),
            observaciones=nota.observaciones,
            created_at=nota.created_at,
            updated_at=nota.updated_at
        ))

    return notas_data

@router.put("/grades/{nota_id}", response_model=NotaDocenteResponse)
def update_grade(
    nota_id: int,
    nota_data: NotaUpdate,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualizar una nota existente"""
    
    # Obtener la nota
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    
    if not nota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nota no encontrada"
        )
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == nota.curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar esta nota"
        )
    
    # Guardar valor anterior para el historial
    valor_anterior = nota.valor_nota
    
    # Actualizar campos
    if nota_data.valor_nota is not None:
        nota.valor_nota = nota_data.valor_nota
    
    if nota_data.fecha_evaluacion is not None:
        from datetime import datetime
        nota.fecha_evaluacion = datetime.strptime(nota_data.fecha_evaluacion, "%Y-%m-%d").date()
    
    if nota_data.observaciones is not None:
        nota.observaciones = nota_data.observaciones
    
    # Actualizar timestamp
    nota.updated_at = datetime.utcnow()
    
    # Crear registro en historial
    historial = HistorialNota(
        nota_id=nota.id,
        estudiante_id=nota.estudiante_id,
        curso_id=nota.curso_id,
        docente_id=current_user.id,
        nota_anterior=valor_anterior,
        nota_nueva=nota.valor_nota,
        tipo_cambio="ACTUALIZACION",
        observaciones=f"Nota actualizada por {current_user.first_name} {current_user.last_name}"
    )
    
    db.add(historial)
    db.commit()
    db.refresh(nota)
    
    return {
        "id": nota.id,
        "estudiante_id": nota.estudiante_id,
        "curso_id": nota.curso_id,
        "valor_nota": float(nota.valor_nota),
        "fecha_evaluacion": nota.fecha_evaluacion.isoformat(),
        "observaciones": nota.observaciones,
        "created_at": nota.created_at,
        "updated_at": nota.updated_at
    }

@router.post("/courses/{curso_id}/grades/bulk")
def update_grades_bulk(
    curso_id: int,
    grades_data: ActualizacionMasivaNotas,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Actualización masiva de notas - ahora un solo registro por estudiante"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    created_count = 0
    updated_count = 0
    errors = []
    
    for nota_data in grades_data.notas:
        try:
            # Buscar si ya existe una nota para este estudiante y curso
            nota_existente = db.query(Nota).filter(
                Nota.estudiante_id == nota_data.estudiante_id,
                Nota.curso_id == curso_id
            ).first()
            
            if nota_existente:
                # Actualizar nota existente
                # Guardar valores anteriores para historial
                valores_anteriores = {
                    'evaluacion1': nota_existente.evaluacion1,
                    'evaluacion2': nota_existente.evaluacion2,
                    'evaluacion3': nota_existente.evaluacion3,
                    'evaluacion4': nota_existente.evaluacion4,
                    'evaluacion5': nota_existente.evaluacion5,
                    'evaluacion6': nota_existente.evaluacion6,
                    'evaluacion7': nota_existente.evaluacion7,
                    'evaluacion8': nota_existente.evaluacion8,
                    'practica1': nota_existente.practica1,
                    'practica2': nota_existente.practica2,
                    'practica3': nota_existente.practica3,
                    'practica4': nota_existente.practica4,
                    'parcial1': nota_existente.parcial1,
                    'parcial2': nota_existente.parcial2,
                }
                
                # Actualizar campos de evaluación
                for field in ['evaluacion1', 'evaluacion2', 'evaluacion3', 'evaluacion4', 
                             'evaluacion5', 'evaluacion6', 'evaluacion7', 'evaluacion8',
                             'practica1', 'practica2', 'practica3', 'practica4',
                             'parcial1', 'parcial2']:
                    if hasattr(nota_data, field) and getattr(nota_data, field) is not None:
                        setattr(nota_existente, field, getattr(nota_data, field))
                
                # Actualizar otros campos
                if nota_data.observaciones:
                    nota_existente.observaciones = nota_data.observaciones
                nota_existente.fecha_registro = nota_data.fecha_registro if hasattr(nota_data, 'fecha_registro') else datetime.now().date()
                nota_existente.updated_at = datetime.utcnow()
                
                # Crear registro en historial
                historial = HistorialNota(
                    nota_id=nota_existente.id,
                    estudiante_id=nota_existente.estudiante_id,
                    curso_id=nota_existente.curso_id,
                    nota_anterior=str(valores_anteriores),
                    nota_nueva=f"Actualización masiva - Estudiante {nota_data.estudiante_id}",
                    motivo_cambio="ACTUALIZACION_MASIVA",
                    usuario_modificacion=f"{current_user.first_name} {current_user.last_name}"
                )
                
                db.add(historial)
                updated_count += 1
                
            else:
                # Crear nueva nota
                nueva_nota = Nota(
                    estudiante_id=nota_data.estudiante_id,
                    curso_id=curso_id,
                    evaluacion1=nota_data.evaluacion1 if hasattr(nota_data, 'evaluacion1') else None,
                    evaluacion2=nota_data.evaluacion2 if hasattr(nota_data, 'evaluacion2') else None,
                    evaluacion3=nota_data.evaluacion3 if hasattr(nota_data, 'evaluacion3') else None,
                    evaluacion4=nota_data.evaluacion4 if hasattr(nota_data, 'evaluacion4') else None,
                    evaluacion5=nota_data.evaluacion5 if hasattr(nota_data, 'evaluacion5') else None,
                    evaluacion6=nota_data.evaluacion6 if hasattr(nota_data, 'evaluacion6') else None,
                    evaluacion7=nota_data.evaluacion7 if hasattr(nota_data, 'evaluacion7') else None,
                    evaluacion8=nota_data.evaluacion8 if hasattr(nota_data, 'evaluacion8') else None,
                    practica1=nota_data.practica1 if hasattr(nota_data, 'practica1') else None,
                    practica2=nota_data.practica2 if hasattr(nota_data, 'practica2') else None,
                    practica3=nota_data.practica3 if hasattr(nota_data, 'practica3') else None,
                    practica4=nota_data.practica4 if hasattr(nota_data, 'practica4') else None,
                    parcial1=nota_data.parcial1 if hasattr(nota_data, 'parcial1') else None,
                    parcial2=nota_data.parcial2 if hasattr(nota_data, 'parcial2') else None,
                    fecha_registro=nota_data.fecha_registro if hasattr(nota_data, 'fecha_registro') else datetime.now().date(),
                    observaciones=nota_data.observaciones if hasattr(nota_data, 'observaciones') else None
                )
                
                db.add(nueva_nota)
                db.flush()  # Para obtener el ID
                
                # Crear registro en historial
                historial = HistorialNota(
                    nota_id=nueva_nota.id,
                    estudiante_id=nueva_nota.estudiante_id,
                    curso_id=nueva_nota.curso_id,
                    nota_anterior=None,
                    nota_nueva=f"Nueva nota - Estudiante {nota_data.estudiante_id}",
                    motivo_cambio="CREACION_MASIVA",
                    usuario_modificacion=f"{current_user.first_name} {current_user.last_name}"
                )
                
                db.add(historial)
                created_count += 1
            
        except Exception as e:
            errors.append(f"Error procesando nota para estudiante {nota_data.estudiante_id}: {str(e)}")
    
    db.commit()
    
    return {
        "message": f"Actualización masiva completada",
        "notas_creadas": created_count,
        "notas_actualizadas": updated_count,
        "errores": errors
    }

@router.post("/courses/{curso_id}/grades/upload-excel")
def upload_grades_from_excel(
    curso_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """
    Cargar notas desde un archivo Excel
    """
    print(f"📊 Procesando archivo Excel: {file.filename}")
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Verificar que el archivo es Excel
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un Excel (.xlsx o .xls)"
        )
    
    try:
        # Leer el archivo Excel
        contents = file.file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        print(f"📋 Archivo Excel leído: {len(df)} filas, {len(df.columns)} columnas")
        print(f"📋 Columnas encontradas: {list(df.columns)}")
        
        # Validar formato del Excel
        required_columns = ['DNI', 'NOMBRE', 'APELLIDO']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Faltan columnas requeridas: {missing_columns}. Formato esperado: DNI, NOMBRE, APELLIDO, EVALUACION1, EVALUACION2, etc."
            )
        
        # Definir tipos de evaluación y sus columnas
        tipos_evaluacion = {
            'EVALUACION': ['EVALUACION1', 'EVALUACION2', 'EVALUACION3', 'EVALUACION4', 
                          'EVALUACION5', 'EVALUACION6', 'EVALUACION7', 'EVALUACION8'],
            'PRACTICA': ['PRACTICA1', 'PRACTICA2', 'PRACTICA3', 'PRACTICA4'],
            'PARCIAL': ['PARCIAL1', 'PARCIAL2']
        }
        
        # Mapeo de columnas del Excel a campos del modelo
        mapeo_columnas = {
            # Evaluaciones
            'EVALUACION1': 'evaluacion1', 'EVALUACION2': 'evaluacion2', 'EVALUACION3': 'evaluacion3', 'EVALUACION4': 'evaluacion4',
            'EVALUACION5': 'evaluacion5', 'EVALUACION6': 'evaluacion6', 'EVALUACION7': 'evaluacion7', 'EVALUACION8': 'evaluacion8',
            # Prácticas
            'PRACTICA1': 'practica1', 'PRACTICA2': 'practica2', 'PRACTICA3': 'practica3', 'PRACTICA4': 'practica4',
            # Parciales
            'PARCIAL1': 'parcial1', 'PARCIAL2': 'parcial2'
        }
        
        # Procesar cada fila del Excel
        notas_procesadas = []
        errores = []
        
        for index, row in df.iterrows():
            try:
                dni = str(row['DNI']).strip()
                nombre = str(row['NOMBRE']).strip()
                apellido = str(row['APELLIDO']).strip()
                
                # Buscar estudiante por DNI
                estudiante = db.query(User).filter(
                    User.dni == dni,
                    User.role == RoleEnum.ESTUDIANTE,
                    User.is_active == True
                ).first()
                
                if not estudiante:
                    errores.append(f"Fila {index + 2}: Estudiante con DNI {dni} no encontrado")
                    continue
                
                # Verificar que el estudiante está matriculado en el ciclo del curso
                matricula = db.query(Matricula).filter(
                    Matricula.estudiante_id == estudiante.id,
                    Matricula.ciclo_id == curso.ciclo_id,
                    Matricula.is_active == True
                ).first()
                
                if not matricula:
                    errores.append(f"Fila {index + 2}: Estudiante {nombre} {apellido} no está matriculado en este ciclo")
                    continue
                
                # Recopilar todos los datos de evaluación para este estudiante
                todos_los_datos = {}
                tipos_procesados = []
                
                # Procesar cada tipo de evaluación y recopilar todos los datos
                for tipo_eval, columnas in tipos_evaluacion.items():
                    datos_tipo = {}
                    for col in columnas:
                        if col in df.columns:
                            valor = row[col]
                            if pd.notna(valor) and str(valor).strip() != '' and str(valor).strip().lower() != 'nan':
                                try:
                                    valor_numerico = float(str(valor).strip())
                                    if valor_numerico >= 0:  # Aceptar valores >= 0
                                        campo_modelo = mapeo_columnas.get(col)
                                        if campo_modelo:
                                            todos_los_datos[campo_modelo] = Decimal(str(valor_numerico))
                                except (ValueError, TypeError):
                                    pass  # Ignorar valores que no se pueden convertir
                    
                    # Si hay datos para este tipo de evaluación, agregarlo a la lista de tipos procesados
                    if datos_tipo:
                        tipos_procesados.append(tipo_eval)
                
                # Si hay datos para procesar, buscar o crear la nota una sola vez
                if todos_los_datos:
                    # Buscar si ya existe una nota para este estudiante y curso
                    nota_existente = db.query(Nota).filter(
                        Nota.estudiante_id == estudiante.id,
                        Nota.curso_id == curso_id
                    ).first()
                    
                    if nota_existente:
                        # Actualizar nota existente
                        for campo, valor in todos_los_datos.items():
                            setattr(nota_existente, campo, valor)
                        nota_existente.updated_at = datetime.utcnow()
                        accion = 'actualizada'
                    else:
                        # Crear nueva nota
                        nueva_nota = Nota(
                            estudiante_id=estudiante.id,
                            curso_id=curso_id,
                            fecha_registro=datetime.now().date(),
                            **todos_los_datos
                        )
                        db.add(nueva_nota)
                        accion = 'creada'
                    
                    notas_procesadas.append({
                        'estudiante': f"{nombre} {apellido}",
                        'dni': dni,
                        'tipos': tipos_procesados,
                        'accion': accion
                    })
                
            except Exception as e:
                errores.append(f"Fila {index + 2}: Error procesando datos - {str(e)}")
        
        # Guardar cambios en la base de datos
        db.commit()
        
        resultado = {
            "mensaje": "Archivo Excel procesado exitosamente",
            "notas_procesadas": len(notas_procesadas),
            "errores": errores,
            "detalles": notas_procesadas[:20],  # Mostrar las primeras 20
            "total_filas": len(df)
        }
        
        return resultado
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error procesando Excel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando archivo Excel: {str(e)}"
        )

@router.get("/courses/{curso_id}/grades/excel-template")
def download_excel_template(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """
    Descargar plantilla Excel para cargar notas
    """
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Obtener estudiantes matriculados en el curso
    estudiantes = db.query(User).join(Matricula).filter(
        Matricula.ciclo_id == curso.ciclo_id,
        Matricula.is_active == True,
        User.role == RoleEnum.ESTUDIANTE,
        User.is_active == True
    ).all()
    
    # Crear DataFrame con plantilla
    data = []
    for estudiante in estudiantes:
        data.append({
            'DNI': estudiante.dni,
            'NOMBRE': estudiante.first_name,
            'APELLIDO': estudiante.last_name,
            'EVALUACION1': '',
            'EVALUACION2': '',
            'EVALUACION3': '',
            'EVALUACION4': '',
            'EVALUACION5': '',
            'EVALUACION6': '',
            'EVALUACION7': '',
            'EVALUACION8': '',
            'PRACTICA1': '',
            'PRACTICA2': '',
            'PRACTICA3': '',
            'PRACTICA4': '',
            'PARCIAL1': '',
            'PARCIAL2': ''
        })
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Notas', index=False)
        
        # Obtener la hoja de trabajo para formatear
        worksheet = writer.sheets['Notas']
        
        # Ajustar ancho de columnas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 20)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Crear respuesta con el archivo
    from fastapi.responses import StreamingResponse
    
    return StreamingResponse(
        io.BytesIO(output.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=plantilla_notas_{curso.nombre.replace(' ', '_')}.xlsx"}
    )

@router.get("/courses/{curso_id}/evaluation-descriptions")
def get_evaluation_descriptions(
    curso_id: int,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Obtener todas las descripciones de evaluaciones de un curso"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Obtener descripciones
    descripciones = db.query(DescripcionEvaluacion).filter(
        DescripcionEvaluacion.curso_id == curso_id
    ).all()
    
    return [
        {
            "id": desc.id,
            "curso_id": desc.curso_id,
            "tipo_evaluacion": desc.tipo_evaluacion,
            "descripcion": desc.descripcion,
            "fecha_evaluacion": desc.fecha_evaluacion.isoformat() if desc.fecha_evaluacion else None,
            "created_at": desc.created_at.isoformat() if desc.created_at else None,
            "updated_at": desc.updated_at.isoformat() if desc.updated_at else None
        }
        for desc in descripciones
    ]

@router.post("/courses/{curso_id}/evaluation-descriptions")
def save_evaluation_description(
    curso_id: int,
    description_data: dict,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Crear o actualizar una descripción de evaluación"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Buscar descripción existente
    descripcion = db.query(DescripcionEvaluacion).filter(
        DescripcionEvaluacion.curso_id == curso_id,
        DescripcionEvaluacion.tipo_evaluacion == description_data['tipo_evaluacion']
    ).first()
    
    if descripcion:
        # Actualizar existente
        descripcion.descripcion = description_data['descripcion']
        if description_data.get('fecha_evaluacion'):
            descripcion.fecha_evaluacion = datetime.strptime(description_data['fecha_evaluacion'], "%Y-%m-%d").date()
        descripcion.updated_at = datetime.utcnow()
    else:
        # Crear nueva
        descripcion = DescripcionEvaluacion(
            curso_id=curso_id,
            tipo_evaluacion=description_data['tipo_evaluacion'],
            descripcion=description_data['descripcion'],
            fecha_evaluacion=datetime.strptime(description_data['fecha_evaluacion'], "%Y-%m-%d").date() if description_data.get('fecha_evaluacion') else datetime.now().date()
        )
        db.add(descripcion)
    
    db.commit()
    db.refresh(descripcion)
    
    return {
        "id": descripcion.id,
        "curso_id": descripcion.curso_id,
        "tipo_evaluacion": descripcion.tipo_evaluacion,
        "descripcion": descripcion.descripcion,
        "fecha_evaluacion": descripcion.fecha_evaluacion.isoformat() if descripcion.fecha_evaluacion else None,
        "created_at": descripcion.created_at.isoformat() if descripcion.created_at else None,
        "updated_at": descripcion.updated_at.isoformat() if descripcion.updated_at else None
    }

@router.delete("/courses/{curso_id}/evaluation-descriptions/{tipo_evaluacion}")
def delete_evaluation_description(
    curso_id: int,
    tipo_evaluacion: str,
    current_user: User = Depends(get_docente_user),
    db: Session = Depends(get_db)
):
    """Eliminar una descripción de evaluación"""
    
    # Verificar que el curso pertenece al docente
    curso = db.query(Curso).filter(
        Curso.id == curso_id,
        Curso.docente_id == current_user.id,
        Curso.is_active == True
    ).first()
    
    if not curso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Curso no encontrado o no tienes permisos para acceder"
        )
    
    # Buscar y eliminar descripción
    descripcion = db.query(DescripcionEvaluacion).filter(
        DescripcionEvaluacion.curso_id == curso_id,
        DescripcionEvaluacion.tipo_evaluacion == tipo_evaluacion
    ).first()
    
    if not descripcion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Descripción de evaluación no encontrada"
        )
    
    db.delete(descripcion)
    db.commit()
    
    return {"message": "Descripción de evaluación eliminada correctamente"}