"""Validaciones del cliente antes de llamar al backend (US-01).

Son las mismas reglas que valida el servidor; aquí solo sirven para avisar
al jugador sin esperar la respuesta. El servidor siempre vuelve a validar.
"""

import re

PATRON_NOMBRE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


def validar_registro(nombre_usuario: str, correo: str, contrasena: str) -> str | None:
    """Devuelve el primer error encontrado, o None si los datos son válidos."""
    if not PATRON_NOMBRE.match(nombre_usuario.strip()):
        return "Usuario: 3 a 30 caracteres, solo letras, números y _"
    if not PATRON_CORREO.match(correo.strip()):
        return "El formato del correo no es válido"
    if not 8 <= len(contrasena) <= 128:
        return "La contraseña debe tener entre 8 y 128 caracteres"
    if not (any(c.isalpha() for c in contrasena) and any(c.isdigit() for c in contrasena)):
        return "La contraseña debe tener al menos una letra y un número"
    return None
