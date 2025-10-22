import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings

class EmailRecuperacionService:
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
    
    def send_password_reset_email(self, to_email: str, reset_token: str):
        """Enviar email con token de recuperación"""
        
        # Verificar si la configuración SMTP está completa
        if not self.smtp_username or not self.smtp_password:
            print(f"❌ Configuración SMTP incompleta en .env")
            print(f"   SMTP_USERNAME: {'✅ Configurado' if self.smtp_username else '❌ Faltante'}")
            print(f"   SMTP_PASSWORD: {'✅ Configurado' if self.smtp_password else '❌ Faltante'}")
            print(f"🔐 Token de recuperación para {to_email}: {reset_token}")
            return False
        
        try:
            print(f"📧 Preparando email para: {to_email}")
            
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = "🔐 Código de Recuperación - Sistema de Notas"
            message["From"] = self.smtp_username
            message["To"] = to_email
            
            # Contenido HTML del email
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                    .content {{ padding: 30px; }}
                    .token {{ background: #f8f9fa; padding: 25px; border-radius: 8px; font-size: 28px; font-weight: bold; text-align: center; margin: 25px 0; border: 2px dashed #667eea; color: #2d3748; letter-spacing: 2px; }}
                    .info-box {{ background: #e8f4fd; padding: 15px; border-radius: 6px; border-left: 4px solid #2196F3; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔄 Recuperación de Contraseña</h1>
                        <p>Sistema de Notas Académicas</p>
                    </div>
                    
                    <div class="content">
                        <p>Hola,</p>
                        <p>Has solicitado restablecer tu contraseña en el <strong>Sistema de Notas</strong>.</p>
                        
                        <p>Utiliza el siguiente código para continuar:</p>
                        
                        <div class="token">
                            {reset_token}
                        </div>
                        
                        <div class="info-box">
                            <p><strong>⚠️ Importante:</strong> Este código es válido por <strong>1 hora</strong>.</p>
                            <p>Si no solicitaste este cambio, ignora este mensaje.</p>
                        </div>
                        
                        <p>Ingresa este código en la página de recuperación para establecer una nueva contraseña.</p>
                        
                        <p>Saludos cordiales,<br>
                        <strong>Equipo del Sistema de Notas</strong></p>
                    </div>
                    
                    <div class="footer">
                        <p>Este es un mensaje automático • No responder a este correo</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Texto plano para clientes de email simples
            text = f"""
            RECUPERACIÓN DE CONTRASEÑA - SISTEMA DE NOTAS
            
            Has solicitado restablecer tu contraseña.
            
            Tu código de verificación es: {reset_token}
            
            ⚠️ Este código expira en 1 hora.
            
            Ingresa este código en el sistema para continuar con el proceso.
            
            Si no solicitaste este cambio, ignora este mensaje.
            
            Saludos,
            Equipo del Sistema de Notas
            """
            
            # Agregar ambas versiones al email
            message.attach(MIMEText(text, "plain"))
            message.attach(MIMEText(html, "html"))
            
            print(f"🔄 Conectando a {self.smtp_server}:{self.smtp_port}...")
            
            # Enviar email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Seguridad TLS
                print(f"🔐 Iniciando sesión con: {self.smtp_username}")
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            print(f"✅ Email enviado exitosamente a: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print(f"❌ Error de autenticación - Verifica tu App Password")
            print(f"🔐 Token (fallback): {reset_token}")
            return False
        except Exception as e:
            print(f"❌ Error enviando email: {str(e)}")
            print(f"🔐 Token (fallback): {reset_token}")
            return False

# Instancia global
email_recuperacion  = EmailRecuperacionService()