-- Script de migración para actualizar la tabla de notas
-- Este script actualiza la estructura de la tabla notas para el nuevo sistema de calificaciones

-- Crear tabla temporal con la nueva estructura
CREATE TABLE notas_new (
    id SERIAL PRIMARY KEY,
    estudiante_id INTEGER NOT NULL REFERENCES users(id),
    curso_id INTEGER NOT NULL REFERENCES cursos(id),
    tipo_evaluacion VARCHAR(50) NOT NULL CHECK (tipo_evaluacion IN ('SEMANAL', 'PRACTICA', 'PARCIAL')),
    valor_nota DECIMAL(4,2) NOT NULL CHECK (valor_nota >= 0 AND valor_nota <= 20),
    peso DECIMAL(3,2) NOT NULL,
    fecha_evaluacion DATE NOT NULL,
    observaciones TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Migrar datos existentes (si los hay)
-- Nota: Este script asume que los datos existentes necesitan ser migrados manualmente
-- ya que la estructura anterior no tiene tipo_evaluacion

-- Eliminar tabla antigua y renombrar la nueva
DROP TABLE IF EXISTS notas CASCADE;
ALTER TABLE notas_new RENAME TO notas;

-- Crear índices para mejorar el rendimiento
CREATE INDEX idx_notas_estudiante_curso ON notas(estudiante_id, curso_id);
CREATE INDEX idx_notas_tipo_evaluacion ON notas(tipo_evaluacion);
CREATE INDEX idx_notas_fecha_evaluacion ON notas(fecha_evaluacion);

-- Comentarios sobre la nueva estructura
COMMENT ON TABLE notas IS 'Tabla de notas con nueva estructura: SEMANAL (peso 0.1), PRACTICA (peso 0.3), PARCIAL (peso 0.3)';
COMMENT ON COLUMN notas.tipo_evaluacion IS 'Tipo de evaluación: SEMANAL, PRACTICA, PARCIAL';
COMMENT ON COLUMN notas.valor_nota IS 'Valor de la nota individual (0-20)';
COMMENT ON COLUMN notas.peso IS 'Peso de la evaluación: 0.1 para semanales, 0.3 para prácticas y parciales';
COMMENT ON COLUMN notas.fecha_evaluacion IS 'Fecha en que se realizó la evaluación';
