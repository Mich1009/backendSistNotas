

# 🎓 Sistema de Notas Académico

Sistema modular para gestión de notas académicas con roles diferenciados (Administrador, Docente, Estudiante).

## 🛠️ Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Python 3.8+**
- **Node.js 16+** y **npm**
- **PostgreSQL 12+**
- **Git**

## ⚙️ Configuración del Backend

### 1. Crear y activar entorno virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar base de datos PostgreSQL

1. **Crear la base de datos:**
   ```sql
   CREATE DATABASE sistema_notas;
   ```

### 4. Configurar variables de entorno

1. **Copiar el archivo de ejemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Editar el archivo `.env` con tus credenciales locales:**
   ```env
   # Configuración de la base de datos
   # Cambia 'usuario' y 'password' por tus credenciales locales de PostgreSQL
   DATABASE_URL=postgresql://tu_usuario:tu_password@localhost:5432/sistema_notas

   # Configuración JWT
   # Cambia por una clave secreta única para tu entorno
   SECRET_KEY=tu_clave_secreta_muy_segura_aqui
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # Configuración de CORS - URLs permitidas para el frontend
   CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

   # Configuración de correo (para recuperación de contraseñas)
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=tu_email@gmail.com
   SMTP_PASSWORD=tu_password_de_aplicacion

   # Configuración general
   DEBUG=True
   ```

### 5. Ejecutar migraciones y poblar la base de datos

```bash
# Ejecutar el seeder para crear datos de prueba
python seeder.py
```

### 6. Iniciar el servidor

```bash
uvicorn main:app --host 0.0.0.0 --port 9001 --reload
```

El servidor estará disponible en: **http://localhost:9001**

## 📊 Documentación de la API

Una vez que el servidor esté ejecutándose, puedes acceder a la documentación interactiva:

- **Swagger UI:** http://localhost:9001/docs
- **ReDoc:** http://localhost:9001/redoc

## 📁 Estructura del Proyecto

```
notas_jhon/
├── backendSistNotas/          # API Backend (FastAPI)
│   ├── app/
│   │   ├── modules/           # Módulos por rol
│   │   │   ├── auth/         # Autenticación
│   │   │   ├── admin/        # Funcionalidades de admin
│   │   │   ├── teacher/      # Funcionalidades de docente
│   │   │   └── student/      # Funcionalidades de estudiante
│   │   ├── shared/           # Modelos y utilidades compartidas
│   │   ├── config.py         # Configuración
│   │   └── database.py       # Conexión a BD
│   ├── main.py              # Punto de entrada
│   ├── seeder.py            # Datos de prueba
│   └── requirements.txt     # Dependencias Python
└── sistemaDeNotas/          # Frontend (React + Vite)
    ├── src/
    │   ├── components/      # Componentes reutilizables
    │   ├── pages/          # Páginas por rol
    │   ├── services/       # Servicios API
    │   └── store/          # Estado global (Zustand)
    └── package.json        # Dependencias Node.js
```

## 👥 Trabajo en Equipo

1. **Cada desarrollador debe:**
   - Copiar `.env.example` a `.env`
   - Configurar sus propias credenciales de base de datos
   - No subir el archivo `.env` al repositorio

2. **Para nuevas funcionalidades:**
   - Crear rama desde `main`
   - Seguir la estructura modular existente
   - Actualizar este README si es necesario

---
