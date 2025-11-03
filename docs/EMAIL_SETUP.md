# Configuración de Email - Sistema de Notas

Este documento explica cómo configurar el sistema de envío de emails para notificaciones y reportes.

## Variables de Entorno

Agrega las siguientes variables a tu archivo `.env`:

```env
# Configuración SMTP para emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password

# Configuración general
DEBUG=True
SECRET_KEY=tu_clave_secreta_muy_segura
DATABASE_URL=postgresql://usuario:password@localhost:5432/sistema_notas

# CORS Origins (JSON array as string)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

## Configuración de Gmail

### Paso 1: Habilitar autenticación de 2 factores

1. Ve a tu cuenta de Google
2. Seguridad → Verificación en dos pasos
3. Activa la verificación en dos pasos

### Paso 2: Generar contraseña de aplicación

1. En tu cuenta de Google, ve a Seguridad
2. Busca "Contraseñas de aplicaciones"
3. Selecciona "Correo" y el dispositivo que uses
4. Copia la contraseña generada (16 caracteres)
5. Usa esta contraseña en `SMTP_PASSWORD`

### Ejemplo de configuración para Gmail:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=profesor@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
```

## Configuración para otros proveedores

### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=profesor@outlook.com
SMTP_PASSWORD=tu_password
```

### Yahoo
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=profesor@yahoo.com
SMTP_PASSWORD=tu_app_password
```

### Servidor SMTP personalizado
```env
SMTP_SERVER=mail.tudominio.com
SMTP_PORT=587
SMTP_USERNAME=profesor@tudominio.com
SMTP_PASSWORD=tu_password
```

## Funcionalidades de Email Disponibles

### 1. Notificación de Evaluaciones Individual
```python
# Endpoint: POST /teacher/courses/{curso_id}/notify-evaluation
# Envía notificación cuando se actualiza una nota específica
```

### 2. Reporte del Curso por Email
```python
# Endpoint: POST /teacher/courses/{curso_id}/send-report-email
# Envía reporte completo del curso a destinatarios específicos
```

### 3. Notificaciones Masivas de Notas
```python
# Endpoint: POST /teacher/courses/{curso_id}/send-grades-notification
# Notifica a todos los estudiantes sus notas actualizadas
```

### 4. Emails Personalizados con Plantillas
```python
# Endpoint: POST /teacher/courses/{curso_id}/send-custom-email
# Usa plantillas predefinidas para diferentes tipos de notificaciones
```

## Plantillas de Email Disponibles

### 1. Reporte General
- **Asunto:** Reporte del curso: {curso}
- **Uso:** Informes periódicos y estadísticas

### 2. Notificación de Notas
- **Asunto:** Notas actualizadas - {curso}
- **Uso:** Informar cambios en calificaciones

### 3. Recordatorio de Evaluación
- **Asunto:** Próxima evaluación - {curso}
- **Uso:** Recordatorios de exámenes o tareas

### 4. Felicitaciones por Aprobar
- **Asunto:** ¡Felicitaciones! Has aprobado {curso}
- **Uso:** Notificar aprobación del curso

### 5. Alerta de Riesgo Académico
- **Asunto:** Importante: Situación académica en {curso}
- **Uso:** Alertar sobre bajo rendimiento

## Variables Disponibles en Plantillas

- `{nombre}` - Nombre completo del estudiante
- `{curso}` - Nombre del curso
- `{nota}` - Nota o promedio del estudiante
- `{estado}` - Estado académico (APROBADO/DESAPROBADO)
- `{profesor}` - Nombre del profesor
- `{fecha}` - Fecha actual
- `{tipo}` - Tipo de evaluación
- Cualquier variable personalizada que definas

## Ejemplos de Uso en el Frontend

### Enviar reporte por email a todos los estudiantes
```javascript
import { emailService } from '../services/apiTeacher';

const enviarReporte = async () => {
  try {
    const resultado = await emailService.sendCourseReport(cursoId, {
      recipients: "all_students",
      subject: "Reporte mensual del curso",
      include_stats: true,
      include_grades: false,
      message: "Estimados estudiantes, adjunto el reporte mensual del curso."
    });
    
    console.log('Emails enviados:', resultado.destinatarios_exitosos);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

### Notificar notas individuales
```javascript
const notificarNotas = async () => {
  try {
    const resultado = await emailService.sendGradesNotification(cursoId, {
      students: "all",
      subject_template: "Tu nota en {curso}",
      message_template: "Hola {nombre}, tu nota actual es: {nota}",
      include_grade_breakdown: true
    });
    
    console.log('Notificaciones enviadas:', resultado.enviados);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

### Usar plantilla personalizada
```javascript
const enviarFelicitaciones = async (estudiantesAprobados) => {
  try {
    const resultado = await emailService.sendCustomEmail(cursoId, {
      template: "felicitacion_aprobado",
      recipients: estudiantesAprobados.map(est => ({id: est.id})),
      custom_variables: {
        periodo: "2024-1"
      }
    });
    
    console.log('Felicitaciones enviadas:', resultado.enviados);
  } catch (error) {
    console.error('Error:', error);
  }
};
```

## Troubleshooting

### Problema: "SMTP no configurado"
- Verifica que todas las variables SMTP estén definidas en el `.env`
- Reinicia el servidor después de cambiar las variables

### Problema: "Authentication failed"
- Para Gmail: usa contraseña de aplicación, no tu contraseña normal
- Verifica que el username sea completo (incluyendo @dominio.com)

### Problema: "Connection timeout"
- Verifica que el puerto sea correcto (587 para TLS, 465 para SSL)
- Algunos proveedores requieren SSL en lugar de TLS

### Problema: "Message rejected"
- Algunos proveedores tienen límites de envío diarios
- Verifica que el contenido no parezca spam
- Asegúrate de que el email remitente esté verificado

## Límites y Consideraciones

### Gmail
- **Límite diario:** 500 emails por día para cuentas gratuitas
- **Límite por minuto:** ~100 emails
- **Recomendación:** Para uso institucional, considera G Suite

### Outlook
- **Límite diario:** 300 emails por día para cuentas gratuitas
- **Límite por minuto:** ~30 emails

### Yahoo
- **Límite diario:** 100 emails por día para cuentas gratuitas
- **Límite por hora:** ~25 emails

## Recomendaciones de Producción

1. **Usa un servicio profesional de email:**
   - SendGrid
   - Mailgun
   - Amazon SES
   - Postmark

2. **Implementa cola de emails:**
   - Para grandes cantidades de estudiantes
   - Usar Celery con Redis/RabbitMQ

3. **Monitoreo:**
   - Logs de emails enviados
   - Seguimiento de bounces y errores
   - Métricas de entrega

4. **Seguridad:**
   - Nunca hardcodear credenciales
   - Usar variables de entorno
   - Rotar passwords regularmente

## Soporte

Si tienes problemas con la configuración de email:

1. Verifica los logs del servidor
2. Prueba la configuración SMTP manualmente
3. Consulta la documentación de tu proveedor de email
4. Considera usar un servicio de email transaccional para producción