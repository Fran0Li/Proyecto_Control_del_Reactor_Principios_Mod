import pytest

from app.core.security import ScryptPasswordHasher
from app.repositories import UsuarioRepository
from app.services.registro_service import (
    CorreoDuplicadoError,
    NombreUsuarioDuplicadoError,
    RegistroService,
)


@pytest.fixture()
def servicio(db_session):
    return RegistroService(UsuarioRepository(db_session), ScryptPasswordHasher(n=2**10))


def test_registro_crea_cuenta_pendiente_de_verificacion(servicio):
    usuario = servicio.registrar("luis", "luis@mail.com", "Secreta123")

    assert usuario.id is not None
    assert usuario.correo_verificado is False


def test_registro_guarda_la_contrasena_hasheada(servicio):
    usuario = servicio.registrar("luis", "luis@mail.com", "Secreta123")

    assert usuario.contrasena_hash != "Secreta123"
    assert servicio.hasher.verificar("Secreta123", usuario.contrasena_hash)


def test_registro_normaliza_el_correo(servicio):
    usuario = servicio.registrar("luis", "  Luis@Mail.COM ", "Secreta123")

    assert usuario.correo == "luis@mail.com"


def test_no_permite_nombre_de_usuario_duplicado(servicio):
    servicio.registrar("luis", "luis@mail.com", "Secreta123")

    with pytest.raises(NombreUsuarioDuplicadoError):
        servicio.registrar("luis", "otro@mail.com", "Secreta123")


def test_no_permite_correo_duplicado_rn01(servicio):
    servicio.registrar("luis", "luis@mail.com", "Secreta123")

    with pytest.raises(CorreoDuplicadoError):
        servicio.registrar("otro", "LUIS@mail.com", "Secreta123")
