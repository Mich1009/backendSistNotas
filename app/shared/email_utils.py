from typing import List, Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_simple_email(subject: str, body: str, to_emails: List[str], *, sender_name: str = "Sistema de Notas") -> Dict:
    """
    Envía un correo de texto plano usando la configuración SMTP de settings.
    Retorna un dict con el resultado del envío por destinatario.
    """
    results = {"sent": [], "failed": []}

    if not to_emails:
        return {"sent": [], "failed": [], "message": "Sin destinatarios"}

    if not settings.smtp_server or not settings.smtp_username or not settings.smtp_password:
        return {
            "sent": [],
            "failed": to_emails,
            "message": "SMTP no configurado. Defina SMTP_SERVER/PORT/USERNAME/PASSWORD en .env"
        }

    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{settings.smtp_username}>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", _charset="utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            for email in to_emails:
                try:
                    msg["To"] = email
                    server.sendmail(settings.smtp_username, email, msg.as_string())
                    results["sent"].append(email)
                except Exception as ex:
                    results["failed"].append({"email": email, "error": str(ex)})
    except Exception as ex:
        return {"sent": [], "failed": to_emails, "message": f"Error SMTP: {str(ex)}"}

    return results


def build_evaluation_email_body(
    estudiante_nombre: str,
    curso_nombre: str,
    evaluacion_label: str,
    nota_valor: Optional[float]
) -> str:
    """
    Construye un cuerpo de correo simple para notificar una nota específica.
    """
    nota_texto = "Sin nota" if nota_valor is None else f"{nota_valor}"
    return (
        f"Hola {estudiante_nombre},\n\n"
        f"Se ha registrado/actualizado tu nota para {evaluacion_label} en el curso '{curso_nombre}'.\n"
        f"Nota: {nota_texto}\n\n"
        f"Por favor, revisa el sistema para más detalles.\n\n"
        f"Saludos,\n"
        f"Sistema de Notas"
    )