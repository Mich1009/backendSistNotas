-- Crear tabla para descripciones de evaluaciones
CREATE TABLE descripciones_evaluacion (
    id SERIAL PRIMARY KEY,
    curso_id INTEGER NOT NULL REFERENCES cursos(id) ON DELETE CASCADE,
    tipo_evaluacion VARCHAR(50) NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_evaluacion DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(curso_id, tipo_evaluacion)
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX idx_descripciones_evaluacion_curso_id ON descripciones_evaluacion(curso_id);
CREATE INDEX idx_descripciones_evaluacion_tipo ON descripciones_evaluacion(tipo_evaluacion);

-- Comentarios para documentar la tabla
COMMENT ON TABLE descripciones_evaluacion IS 'Almacena las descripciones de cada tipo de evaluación por curso';
COMMENT ON COLUMN descripciones_evaluacion.tipo_evaluacion IS 'Tipo de evaluación: evaluacion1, evaluacion2, practica1, practica2, parcial1, parcial2, etc.';
COMMENT ON COLUMN descripciones_evaluacion.descripcion IS 'Descripción detallada de la evaluación';
COMMENT ON COLUMN descripciones_evaluacion.fecha_evaluacion IS 'Fecha programada para la evaluación';