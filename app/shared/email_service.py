"""
Servicio de envío de emails
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password

    def _create_smtp_connection(self):
        """Crear conexión SMTP"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            return server
        except Exception as e:
            logger.error(f"Error al conectar con SMTP: {e}")
            raise

    def _create_grade_notification_html(
        self,
        student_name: str,
        course_name: str,
        evaluation_type: str,
        grade_value: float,
        evaluation_date: str,
        description: Optional[str] = None,
    ) -> str:
        """Crear plantilla HTML para notificación de nota"""

        description_section = ""
        if description:
            description_section = f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                <h4 style="color: #495057; margin: 0 0 10px 0;">Descripción de la Evaluación:</h4>
                <p style="margin: 0; color: #6c757d;">{description}</p>
            </div>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Nueva Calificación Registrada</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 10px;">
            <div style="background-color: #007bff; color: white; padding: 10px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="margin: 0;">📚 Nueva Calificación Registrada</h1>
            </div>
            
            <div style="background-color: #ffffff; padding: 20px; border: 1px solid #dee2e6; border-radius: 0 0 10px 10px;">
                <p style="font-size: 16px; margin-bottom: 20px;">Estimado/a <strong>{student_name}</strong>,</p>
                
                <p>Se ha registrado una nueva calificación en tu expediente académico:</p>
                
                <div style="background-color: #e9ecef; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #495057;">Curso:</td>
                            <td style="padding: 8px 0; color: #6c757d;">{course_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #495057;">Tipo de Evaluación:</td>
                            <td style="padding: 8px 0; color: #6c757d;">{evaluation_type}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #495057;">Calificación:</td>
                            <td style="padding: 8px 0; color: #007bff; font-weight: bold; font-size: 18px;">{grade_value}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; color: #495057;">Fecha de Evaluación:</td>
                            <td style="padding: 8px 0; color: #6c757d;">{evaluation_date}</td>
                        </tr>
                    </table>
                </div>
                {description_section}
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 14px; margin: 0;">
                        Este es un mensaje automático del Sistema de Gestión Académica. 
                        Para más información, ingresa a tu portal estudiantil.
                    </p>
                </div>
            </div>
            
            <div style="text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px;">
                <p>© {datetime.now().year} Sistema de Gestión Académica</p>
            </div>
        </body>
        </html>
        """
        return html_content

    def send_grade_notification(
        self,
        student_email: str,
        student_name: str,
        course_name: str,
        evaluation_type: str,
        grade_value: float,
        evaluation_date: str,
        description: Optional[str] = None,
    ) -> bool:
        """Enviar notificación de nueva calificación"""
        try:
            # Crear mensaje
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Nueva Calificación - {course_name}"
            msg["From"] = self.smtp_username
            msg["To"] = student_email

            # Crear contenido HTML
            html_content = self._create_grade_notification_html(
                student_name,
                course_name,
                evaluation_type,
                grade_value,
                evaluation_date,
                description,
            )

            # Crear contenido de texto plano como fallback
            text_content = f"""
Nueva Calificación Registrada

Estimado/a {student_name},

Se ha registrado una nueva calificación en tu expediente académico:

Curso: {course_name}
Tipo de Evaluación: {evaluation_type}
Calificación: {grade_value}
Fecha de Evaluación: {evaluation_date}
"""

            if description:
                text_content += f"\nDescripción de la Evaluación:\n{description}\n"

            text_content += """
Este es un mensaje automático del Sistema de Gestión Académica.
Para más información, ingresa a tu portal estudiantil.
"""

            # Adjuntar contenido
            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            # Enviar email
            with self._create_smtp_connection() as server:
                server.send_message(msg)

            logger.info(f"Email enviado exitosamente a {student_email}")
            return True

        except Exception as e:
            logger.error(f"Error al enviar email a {student_email}: {e}")
            return False


# Instancia global del servicio
email_service = EmailService()
