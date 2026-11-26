"""Crea la cuenta de administrador (US-28), o le da ese rol a una cuenta que ya existe.

El rol no se puede pedir al registrarse: solo se da desde aquí, con acceso al servidor.

    docker compose exec server python -m app.scripts.crear_admin \
        --usuario admin --correo admin@reactor.cr

La contraseña se pide por teclado (o se pasa en la variable ADMIN_CONTRASENA).
"""

import argparse
import getpass
import os
import sys

from app.api.routes.auth import contrasena_segura
from app.db.session import SessionLocal
from app.models.usuario import ROL_ADMIN, Usuario
from app.repositories import UsuarioRepository
from app.services.registro_service import RegistroError, RegistroService


def crear_admin(
    repo: UsuarioRepository, nombre_usuario: str, correo: str, contrasena: str
) -> Usuario:
    """Si ya hay una cuenta con ese nombre o correo, la promueve; si no, la crea verificada."""
    usuario = repo.obtener_por_nombre_usuario(nombre_usuario) or repo.obtener_por_correo(
        correo.strip().lower()
    )
    if usuario is None:
        usuario = RegistroService(repo).registrar(nombre_usuario, correo, contrasena)
    usuario.rol = ROL_ADMIN
    usuario.correo_verificado = True  # la cuenta la crea el equipo, no hace falta el correo
    usuario.bloqueado = False
    return repo.guardar(usuario)


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crear la cuenta de administrador")
    parser.add_argument("--usuario", required=True)
    parser.add_argument("--correo", required=True)
    datos = parser.parse_args(argumentos)
    contrasena = os.environ.get("ADMIN_CONTRASENA") or getpass.getpass("Contraseña: ")
    try:
        if len(contrasena) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        contrasena_segura(contrasena)  # la misma regla que en el registro
    except ValueError as error:
        print(error)
        return 1
    with SessionLocal() as sesion:
        try:
            admin = crear_admin(UsuarioRepository(sesion), datos.usuario, datos.correo, contrasena)
        except RegistroError as error:
            print(error)
            return 1
    print(f"Listo: {admin.nombre_usuario} (id {admin.id}) es administrador")
    return 0


if __name__ == "__main__":
    sys.exit(main())
