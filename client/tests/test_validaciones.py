import pytest

from src.validaciones import validar_registro


def test_datos_validos_no_devuelven_error():
    assert validar_registro("luis_07", "luis@mail.com", "Secreta123") is None


@pytest.mark.parametrize(
    ("nombre", "correo", "contrasena", "fragmento"),
    [
        ("lu", "luis@mail.com", "Secreta123", "Usuario"),
        ("con espacio", "luis@mail.com", "Secreta123", "Usuario"),
        ("luis", "luis.mail.com", "Secreta123", "correo"),
        ("luis", "luis@mail", "Secreta123", "correo"),
        ("luis", "luis@mail.com", "Corta1", "entre 8"),
        ("luis", "luis@mail.com", "sololetras", "letra y un número"),
        ("luis", "luis@mail.com", "12345678", "letra y un número"),
    ],
)
def test_datos_invalidos_devuelven_el_error(nombre, correo, contrasena, fragmento):
    error = validar_registro(nombre, correo, contrasena)

    assert error is not None
    assert fragmento in error
