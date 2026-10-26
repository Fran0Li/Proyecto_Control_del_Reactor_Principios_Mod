"""Pruebas del adaptador Serial con un puerto y un reloj falsos (sin hardware)."""

import pytest

from src.entrada.serial_entrada import EntradaSerial


class PuertoFalso:
    def __init__(self):
        self.pendiente = b""
        self.cerrado = False
        self.fallar = False

    def enviar(self, texto: str) -> None:
        self.pendiente += texto.encode()

    def read(self, _n):
        if self.fallar:
            raise OSError("cable desconectado")
        datos, self.pendiente = self.pendiente, b""
        return datos

    def close(self):
        self.cerrado = True


class Reloj:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture()
def entorno():
    puertos = []

    def abrir(_nombre):
        puerto = PuertoFalso()
        puertos.append(puerto)
        return puerto

    reloj = Reloj()
    entrada = EntradaSerial("COM3", abrir=abrir, reloj=reloj)
    entrada.revisar()  # abre el puerto
    return entrada, puertos, reloj


def test_saludo_conecta_y_botones_generan_entradas(entorno):
    entrada, puertos, _ = entorno
    puertos[0].enviar("HELLO CR-PAD-01 1.0\nBTN UP PRESS\nBTN UP RELEASE\n")
    entrada.revisar()

    assert entrada.estado == "conectado"
    assert entrada.origen == "hardware"
    assert entrada.obtener_avisos() == [
        {"tipo": "dispositivo", "estado": "conectado", "id": "CR-PAD-01"}
    ]
    assert entrada.obtener() == [("arriba", "presionado"), ("arriba", "liberado")]


def test_linea_partida_en_dos_lecturas(entorno):
    entrada, puertos, _ = entorno
    puertos[0].enviar("BTN LE")
    entrada.revisar()
    assert entrada.obtener() == []
    puertos[0].enviar("FT PRESS\n")
    entrada.revisar()
    assert entrada.obtener() == [("izquierda", "presionado")]


def test_linea_invalida_se_descarta_sin_afectar_las_demas(entorno):
    entrada, puertos, _ = entorno
    puertos[0].enviar("BTN JUMP PRESS\nBTN ACTION PRESS\n")
    entrada.revisar()
    assert entrada.lineas_invalidas == 1
    assert entrada.obtener() == [("accion", "presionado")]


def test_presionado_repetido_no_duplica(entorno):
    entrada, puertos, _ = entorno
    puertos[0].enviar("BTN UP PRESS\nBTN UP PRESS\nBTN DOWN RELEASE\n")
    entrada.revisar()
    assert entrada.obtener() == [("arriba", "presionado")]


def test_sin_latidos_suelta_controles_y_avisa(entorno):
    entrada, puertos, reloj = entorno
    puertos[0].enviar("HELLO CR-PAD-01 1.0\nBTN RIGHT PRESS\nBTN ACTION PRESS\n")
    entrada.revisar()
    entrada.obtener()
    entrada.obtener_avisos()

    reloj.t += 2.5
    entrada.revisar()
    assert entrada.estado == "conectado"  # todavía dentro de los 3 s

    reloj.t += 1.0
    entrada.revisar()
    assert entrada.estado == "desconectado"
    assert puertos[0].cerrado
    assert entrada.obtener() == [("accion", "liberado"), ("derecha", "liberado")]
    assert entrada.obtener_avisos() == [
        {"tipo": "dispositivo", "estado": "desconectado", "id": "CR-PAD-01"}
    ]


def test_latidos_mantienen_la_conexion(entorno):
    entrada, puertos, reloj = entorno
    puertos[0].enviar("HELLO CR-PAD-01 1.0\n")
    for _ in range(10):
        reloj.t += 1.0
        puertos[0].enviar("HB\n")
        entrada.revisar()
    assert entrada.estado == "conectado"


def test_error_de_lectura_desconecta_y_reintenta_cada_2_s(entorno):
    entrada, puertos, reloj = entorno
    puertos[0].enviar("HELLO CR-PAD-01 1.0\nBTN UP PRESS\n")
    entrada.revisar()
    entrada.obtener()

    puertos[0].fallar = True
    entrada.revisar()
    assert entrada.estado == "desconectado"
    assert entrada.obtener() == [("arriba", "liberado")]

    reloj.t += 1.0
    entrada.revisar()
    assert len(puertos) == 1  # todavía no reintenta

    reloj.t += 1.0
    entrada.revisar()
    assert len(puertos) == 2  # reabrió el puerto
    puertos[1].enviar("HELLO CR-PAD-01 1.0\n")
    entrada.revisar()
    assert entrada.estado == "conectado"


def test_puerto_que_no_existe_no_rompe_el_cliente():
    def abrir(_nombre):
        raise OSError("no existe COM9")

    reloj = Reloj()
    entrada = EntradaSerial("COM9", abrir=abrir, reloj=reloj)
    entrada.revisar()
    reloj.t += 5
    entrada.revisar()
    assert entrada.estado == "desconectado"
    assert entrada.obtener() == []


def test_simulador_usa_origen_simulador():
    assert EntradaSerial("socket://localhost:7777").origen == "simulador"


def test_con_pyserial_real_por_loopback():
    """Integración con pyserial: el puerto loop:// devuelve lo que se escribe."""
    pytest.importorskip("serial")
    import serial

    puerto = serial.serial_for_url("loop://", timeout=0)
    entrada = EntradaSerial("loop://", abrir=lambda _n: puerto)
    entrada.revisar()
    puerto.write(b"HELLO CR-PAD-01 1.0\r\nBTN DOWN PRESS\r\n")
    entrada.revisar()
    assert entrada.estado == "conectado"
    assert entrada.obtener() == [("abajo", "presionado")]
