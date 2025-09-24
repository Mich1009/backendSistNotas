-- Script SQL para PostgreSQL - Sistema de Notas

-- Crear extensión para UUID si es necesario
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tipos ENUM
CREATE TYPE role_enum AS ENUM ('admin', 'docente', 'estudiante');

-- Tabla de usuarios (unificada para todos los roles)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(15),
    role role_enum NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    last_ip VARCHAR(45),
    last_user_agent VARCHAR(255)
);

-- Tabla de tokens de recuperación de contraseña
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de carreras
CREATE TABLE carreras (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    descripcion TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de ciclos académicos
CREATE TABLE ciclos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE, -- Ej: "2025-I"
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de cursos
CREATE TABLE cursos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    carrera_id INTEGER NOT NULL REFERENCES carreras(id),
    ciclo_numero INTEGER NOT NULL, -- 1, 2, 3, etc.
    creditos INTEGER DEFAULT 3,
    horas_teoricas INTEGER DEFAULT 2,
    horas_practicas INTEGER DEFAULT 2,
    docente_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de matrículas de estudiantes
CREATE TABLE matriculas (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES users(id),
    curso_id INTEGER NOT NULL REFERENCES cursos(id),
    ciclo_id INTEGER NOT NULL REFERENCES ciclos(id),
    fecha_matricula TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(estudiante_id, curso_id, ciclo_id)
);

-- Tabla de notas
CREATE TABLE notas (
    id SERIAL PRIMARY KEY,
    matricula_id INTEGER NOT NULL REFERENCES matriculas(id),
    nota1 DECIMAL(4,2) CHECK (nota1 >= 0 AND nota1 <= 20),
    nota2 DECIMAL(4,2) CHECK (nota2 >= 0 AND nota2 <= 20),
    nota3 DECIMAL(4,2) CHECK (nota3 >= 0 AND nota3 <= 20),
    nota4 DECIMAL(4,2) CHECK (nota4 >= 0 AND nota4 <= 20),
    promedio DECIMAL(4,2) GENERATED ALWAYS AS (
        ROUND((COALESCE(nota1,0) + COALESCE(nota2,0) + COALESCE(nota3,0) + COALESCE(nota4,0)) / 4, 2)
    ) STORED,
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Tabla de notificaciones
CREATE TABLE notificaciones (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    titulo VARCHAR(100) NOT NULL,
    mensaje TEXT NOT NULL,
    tipo VARCHAR(20) DEFAULT 'info', -- info, warning, error, success
    leido BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de logs de actividad
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    accion VARCHAR(255) NOT NULL,
    detalles JSONB,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejorar el rendimiento
CREATE INDEX idx_users_dni ON users(dni);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_cursos_docente ON cursos(docente_id);
CREATE INDEX idx_matriculas_estudiante ON matriculas(estudiante_id);
CREATE INDEX idx_matriculas_curso ON matriculas(curso_id);
CREATE INDEX idx_notas_matricula ON notas(matricula_id);
CREATE INDEX idx_notificaciones_user ON notificaciones(user_id);
CREATE INDEX idx_logs_user ON logs(user_id);

-- Función para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notas_updated_at BEFORE UPDATE ON notas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insertar datos iniciales
INSERT INTO carreras (nombre, codigo, descripcion) VALUES
('Ingeniería de Sistemas', 'IS', 'Carrera de Ingeniería de Sistemas e Informática'),
('Ingeniería Civil', 'IC', 'Carrera de Ingeniería Civil'),
('Administración', 'ADM', 'Carrera de Administración de Empresas'),
('Contabilidad', 'CONT', 'Carrera de Contabilidad y Finanzas');

INSERT INTO ciclos (nombre, fecha_inicio, fecha_fin) VALUES
('2024-I', '2024-03-01', '2024-07-31'),
('2024-II', '2024-08-01', '2024-12-31'),
('2025-I', '2025-03-01', '2025-07-31');

-- Insertar algunos cursos de ejemplo
INSERT INTO cursos (nombre, codigo, carrera_id, ciclo_numero, creditos) VALUES
('Programación I', 'PROG1', 1, 1, 4),
('Matemática Básica', 'MAT1', 1, 1, 3),
('Algoritmos y Estructuras de Datos', 'AED', 1, 2, 4),
('Base de Datos I', 'BD1', 1, 3, 4),
('Ingeniería de Software', 'IS', 1, 4, 3);