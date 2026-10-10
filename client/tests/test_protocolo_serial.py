import pytest

from src.entrada.protocolo_serial import Boton, Latido, Saludo, interpretar_linea


@pytest.mark.parametrize(
    ("linea", "esperado"),
    [
        ("BTN UP PRESS", Boton("arriba", "presionado")),
        ("BTN DOWN RELEASE", Boton("abajo", "liberado")),
        ("BTN LEFT PRESS\r\n", Boton("izquierda", "presionado")),
        ("BTN RIGHT RELEASE", Boton("derecha", "liberado")),
        ("BTN ACTION PRESS", Boton("accion", "presionado")),
        ("HB", Latido()),
        ("HELLO CR-PAD-01 1.0", Saludo("CR-PAD-01", "1.0")),
    ],
)
def test_lineas_validas(linea, esperado):
    assert interpretar_linea(linea) == esperado


@pytest.mark.parametrize(
    "linea",
    ["BTN JUMP PRESS", "BTN UP HOLD", "btn up press", "BTN UP", "HELLO", "", "HB HB", "basura"],
)
def test_lineas_invalidas_se_descartan(linea):
    assert interpretar_linea(linea) is None
