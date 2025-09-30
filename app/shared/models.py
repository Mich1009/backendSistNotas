"""
Modelos compartidos del sistema
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Numeric, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base
import enum

class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    DOCENTE = "docente"
    ESTUDIANTE = "estudiante"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    dni = Column(String(8), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(15), nullable=True)
    role = Column(Enum(RoleEnum), nullable=False)
    
    # Campos específicos para estudiantes
    fecha_nacimiento = Column(Date, nullable=True)
    direccion = Column(String(255), nullable=True)
    nombre_apoderado = Column(String(100), nullable=True)
    telefono_apoderado = Column(String(15), nullable=True)
    
    # Campos específicos para docentes
    especialidad = Column(String(100), nullable=True)
    grado_academico = Column(String(50), nullable=True)
    fecha_ingreso = Column(Date, nullable=True)
    
    # Campos comunes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_ip = Column(String(45), nullable=True)
    last_user_agent = Column(String(255), nullable=True)
    
    # Relaciones - usando strings para evitar importaciones circulares
    docente_cursos = relationship("Curso", back_populates="docente", foreign_keys="Curso.docente_id")
    estudiante_matriculas = relationship("Matricula", back_populates="estudiante", foreign_keys="Matricula.estudiante_id")
    notas_estudiante = relationship("Nota", back_populates="estudiante", foreign_keys="Nota.estudiante_id")
    
    def __repr__(self):
        return f"<User(dni={self.dni}, email={self.email}, role={self.role})>"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")

class Carrera(Base):
    __tablename__ = "carreras"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    duracion_ciclos = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    ciclos = relationship("Ciclo", back_populates="carrera")
    matriculas = relationship("Matricula", back_populates="carrera")
    
    def __repr__(self):
        return f"<Carrera(codigo={self.codigo}, nombre={self.nombre})>"

class Ciclo(Base):
    __tablename__ = "ciclos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    carrera_id = Column(Integer, ForeignKey("carreras.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    carrera = relationship("Carrera", back_populates="ciclos")
    cursos = relationship("Curso", back_populates="ciclo")
    matriculas = relationship("Matricula", back_populates="ciclo")
    
    def __repr__(self):
        return f"<Ciclo(nombre={self.nombre}, carrera={self.carrera.nombre if self.carrera else 'N/A'})>"

class Curso(Base):
    __tablename__ = "cursos"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    codigo = Column(String(10), unique=True, nullable=False)
    creditos = Column(Integer, nullable=False)
    horas_semanales = Column(Integer, nullable=False)
    ciclo_id = Column(Integer, ForeignKey("ciclos.id"), nullable=False)
    docente_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    ciclo = relationship("Ciclo", back_populates="cursos")
    docente = relationship("User", back_populates="docente_cursos", foreign_keys=[docente_id])
    matriculas = relationship("Matricula", back_populates="curso")
    notas = relationship("Nota", back_populates="curso")
    
    def __repr__(self):
        return f"<Curso(codigo={self.codigo}, nombre={self.nombre})>"

class Matricula(Base):
    __tablename__ = "matriculas"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    carrera_id = Column(Integer, ForeignKey("carreras.id"), nullable=False)
    ciclo_id = Column(Integer, ForeignKey("ciclos.id"), nullable=False)
    fecha_matricula = Column(Date, nullable=False)
    estado = Column(String(20), default="activa")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    estudiante = relationship("User", back_populates="estudiante_matriculas", foreign_keys=[estudiante_id])
    curso = relationship("Curso", back_populates="matriculas")
    carrera = relationship("Carrera", back_populates="matriculas")
    ciclo = relationship("Ciclo", back_populates="matriculas")
    
    def __repr__(self):
        return f"<Matricula(estudiante_id={self.estudiante_id}, curso_id={self.curso_id})>"

class Nota(Base):
    __tablename__ = "notas"
    
    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    curso_id = Column(Integer, ForeignKey("cursos.id"), nullable=False)
    tipo_evaluacion = Column(String(50), nullable=False)
    nota = Column(Numeric(4, 2), nullable=False)
    peso = Column(Numeric(3, 2), nullable=False)
    fecha_evaluacion = Column(Date, nullable=False)
    observaciones = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    estudiante = relationship("User", back_populates="notas_estudiante", foreign_keys=[estudiante_id])
    curso = relationship("Curso", back_populates="notas")
    historial = relationship("HistorialNota", back_populates="nota")
    
    def __repr__(self):
        return f"<Nota(estudiante_id={self.estudiante_id}, curso_id={self.curso_id}, nota={self.nota})>"

class HistorialNota(Base):
    __tablename__ = "historial_notas"
    
    id = Column(Integer, primary_key=True, index=True)
    nota_id = Column(Integer, ForeignKey("notas.id"), nullable=False)
    nota_anterior = Column(Numeric(4, 2), nullable=True)
    nota_nueva = Column(Numeric(4, 2), nullable=False)
    motivo_cambio = Column(String(255), nullable=False)
    usuario_modificacion = Column(String(100), nullable=False)
    fecha_modificacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    nota = relationship("Nota", back_populates="historial")
    
    def __repr__(self):
        return f"<HistorialNota(nota_id={self.nota_id}, nota_anterior={self.nota_anterior}, nota_nueva={self.nota_nueva})>"