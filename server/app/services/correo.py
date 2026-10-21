"""Envío de correos (US-02).

Sin SMTP configurado se usa `EnviadorConsola`, que imprime el correo en la consola del servidor:
así se puede probar todo sin una cuenta de correo. Para cambiar de uno a otro basta el `.env`.
"""

import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage

from app.core.config import settings


class CorreoNoEnviadoError(Exception):
    pass


class EnviadorCorreo(ABC):
    @abstractmethod
    def enviar(self, destino: str, asunto: str, cuerpo: str) -> None: ...


class EnviadorConsola(EnviadorCorreo):
    def enviar(self, destino: str, asunto: str, cuerpo: str) -> None:
        print(f"\n--- Correo para {destino} ---\nAsunto: {asunto}\n\n{cuerpo}\n---\n", flush=True)


class EnviadorSMTP(EnviadorCorreo):
    def __init__(self, host: str, puerto: int, usuario: str, contrasena: str) -> None:
        self.host = host
        self.puerto = puerto
        self.usuario = usuario
        self.contrasena = contrasena

    def enviar(self, destino: str, asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje["From"] = f"Control del Reactor <{self.usuario}>"
        mensaje["To"] = destino
        mensaje["Subject"] = asunto
        mensaje.set_content(cuerpo)
        try:
            with smtplib.SMTP(self.host, self.puerto, timeout=10) as smtp:
                smtp.starttls()
                smtp.login(self.usuario, self.contrasena)
                smtp.send_message(mensaje)
        except (smtplib.SMTPException, OSError) as error:
            raise CorreoNoEnviadoError(str(error)) from error


def crear_enviador() -> EnviadorCorreo:
    if not settings.smtp_host:
        return EnviadorConsola()
    return EnviadorSMTP(
        settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password
    )
