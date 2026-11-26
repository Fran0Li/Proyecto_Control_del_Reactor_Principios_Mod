"""Rol de administrador (US-28): acceso, estadísticas, bloqueo de cuentas y partidas colgadas."""

import pytest
from fastapi.testclient import TestClient

from app.core.security import ScryptPasswordHasher, crear_token_acceso
from app.db.session import get_session
from app.main import app
from app.models.partida import EstadoPartida, Partida
from app.models.usuario import ROL_ADMIN, Usuario
from app.realtime.gestor_motores import gestor_motores
from app.realtime.motor_partida import FINALIZADA, MotorPartida
from app.repositories import PartidaRepository, UsuarioRepository
from app.scripts import crear_admin
from app.services.google_oauth import PerfilGoogle
from app.services.login_social_service import CuentaBloqueadaError, LoginSocialService
from app.services.registro_service import RegistroService


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    gestor_motores.limpiar()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        gestor_motores.limpiar()


def crear_usuario(db_session, nombre, rol="jugador"):
    usuario = Usuario(
        nombre_usuario=nombre, correo=f"{nombre}@mail.com", contrasena_hash="hash", rol=rol
    )
    return UsuarioRepository(db_session).crear(usuario)


def con_token(usuario):
    return {"Authorization": f"Bearer {crear_token_acceso(usuario.id, usuario.version_sesion)}"}


@pytest.fixture()
def admin(db_session):
    return crear_usuario(db_session, "admin", rol=ROL_ADMIN)


@pytest.fixture()
def ana(db_session):
    return crear_usuario(db_session, "ana")


def partida(db_session, estado, *resultados):
    """`resultados`: (usuario, puntaje) de cada jugador."""
    repo = PartidaRepository(db_session)
    nueva = repo.crear(Partida(estado=EstadoPartida.en_curso, escenario="laboratorio"))
    for usuario, _ in resultados:
        repo.agregar_participante(nueva.id, usuario.id)
    if estado == EstadoPartida.finalizada:
        puestos = sorted(resultados, key=lambda r: -r[1])
        repo.guardar_resultado(
            nueva, {u.id: (p, puesto) for puesto, (u, p) in enumerate(puestos, start=1)}
        )
    else:
        repo.cambiar_estado(nueva, estado)
    return nueva


# acceso


@pytest.mark.parametrize(
    ("metodo", "ruta"),
    [
        ("get", "/admin/estadisticas"),
        ("get", "/admin/usuarios"),
        ("get", "/admin/partidas"),
        ("post", "/admin/usuarios/1/bloquear"),
        ("post", "/admin/usuarios/1/desbloquear"),
        ("post", "/admin/partidas/1/cerrar"),
    ],
)
def test_un_jugador_recibe_acceso_denegado(client, ana, metodo, ruta):
    respuesta = getattr(client, metodo)(ruta, headers=con_token(ana))

    assert respuesta.status_code == 403
    assert respuesta.json()["detail"] == "Solo un administrador puede hacer esto"


def test_sin_sesion_pide_iniciar_sesion(client):
    assert client.get("/admin/estadisticas").status_code == 401


def test_el_login_dice_el_rol_de_la_cuenta(client, db_session):
    repo = UsuarioRepository(db_session)
    usuario = RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        "luis", "luis@mail.com", "Secreta123"
    )
    usuario.correo_verificado = True
    repo.guardar(usuario)

    datos = client.post("/auth/login", json={"usuario": "luis", "contrasena": "Secreta123"}).json()

    assert datos["usuario"]["rol"] == "jugador"


# estadísticas y listados


def test_el_admin_ve_las_estadisticas_globales(client, db_session, admin, ana):
    beto = crear_usuario(db_session, "beto")
    partida(db_session, EstadoPartida.finalizada, (ana, 300), (beto, 120))
    partida(db_session, EstadoPartida.finalizada, (beto, 450))
    partida(db_session, EstadoPartida.esperando, (ana, 0))

    datos = client.get("/admin/estadisticas", headers=con_token(admin)).json()

    assert datos["usuarios_registrados"] == 3
    assert datos["usuarios_bloqueados"] == 0
    assert datos["partidas_jugadas"] == 2 and datos["partidas_activas"] == 1
    mejores = [(m["nombre"], m["puntaje"]) for m in datos["mejores_puntajes"]]
    assert mejores == [("beto", 450), ("ana", 300), ("beto", 120)]


def test_el_admin_lista_los_usuarios(client, admin, ana):
    datos = client.get("/admin/usuarios", headers=con_token(admin)).json()

    assert [(u["nombre_usuario"], u["rol"], u["bloqueado"]) for u in datos] == [
        ("admin", ROL_ADMIN, False),
        ("ana", "jugador", False),
    ]


def test_el_admin_ve_las_partidas_activas(client, db_session, admin, ana):
    partida(db_session, EstadoPartida.finalizada, (ana, 10))
    activa = partida(db_session, EstadoPartida.en_curso, (ana, 0))

    datos = client.get("/admin/partidas", headers=con_token(admin)).json()

    assert datos == [
        {"id": activa.id, "estado": "en_curso", "escenario": "laboratorio", "jugadores": 1}
    ]


# bloquear y desbloquear


def test_bloquear_corta_la_sesion_abierta_del_jugador(client, db_session, admin, ana):
    token_viejo = con_token(ana)

    respuesta = client.post(f"/admin/usuarios/{ana.id}/bloquear", headers=con_token(admin))

    assert respuesta.status_code == 200 and respuesta.json()["bloqueado"]
    assert client.get("/auth/yo", headers=token_viejo).status_code == 401


def test_una_cuenta_bloqueada_no_puede_entrar_hasta_que_la_desbloquean(client, db_session, admin):
    repo = UsuarioRepository(db_session)
    luis = RegistroService(repo, ScryptPasswordHasher(n=2**10)).registrar(
        "luis", "luis@mail.com", "Secreta123"
    )
    luis.correo_verificado = True
    repo.guardar(luis)
    login = {"usuario": "luis", "contrasena": "Secreta123"}

    client.post(f"/admin/usuarios/{luis.id}/bloquear", headers=con_token(admin))
    bloqueado = client.post("/auth/login", json=login)
    client.post(f"/admin/usuarios/{luis.id}/desbloquear", headers=con_token(admin))
    desbloqueado = client.post("/auth/login", json=login)

    assert bloqueado.status_code == 423
    assert bloqueado.json()["detail"] == "Tu cuenta fue bloqueada por un administrador"
    assert desbloqueado.status_code == 200


def test_no_se_puede_bloquear_a_un_administrador(client, db_session, admin):
    otro = crear_usuario(db_session, "otro_admin", rol=ROL_ADMIN)

    for usuario in (otro, admin):
        respuesta = client.post(f"/admin/usuarios/{usuario.id}/bloquear", headers=con_token(admin))
        assert respuesta.status_code == 409


def test_bloquear_a_alguien_que_no_existe_da_404(client, admin):
    assert client.post("/admin/usuarios/9999/bloquear", headers=con_token(admin)).status_code == 404


# cerrar partidas colgadas


def test_cerrar_una_partida_sin_motor_la_marca_como_finalizada(client, db_session, admin, ana):
    colgada = partida(db_session, EstadoPartida.en_curso, (ana, 0))

    respuesta = client.post(f"/admin/partidas/{colgada.id}/cerrar", headers=con_token(admin))

    assert respuesta.status_code == 202
    db_session.refresh(colgada)
    assert colgada.estado == EstadoPartida.finalizada


def test_cerrar_una_partida_en_curso_la_termina_en_el_motor(client, db_session, admin, ana):
    en_curso = partida(db_session, EstadoPartida.en_curso, (ana, 0))
    motor = MotorPartida(en_curso.id)
    gestor_motores._motores[en_curso.id] = motor  # sin ponerlo a correr: basta con su estado
    motor.agregar_jugador(ana.id, "ana")
    motor.iniciar_partida(300, 500)

    respuesta = client.post(f"/admin/partidas/{en_curso.id}/cerrar", headers=con_token(admin))

    assert respuesta.status_code == 202
    assert motor.estado_partida == FINALIZADA


def test_no_se_puede_cerrar_una_partida_terminada_o_que_no_existe(client, db_session, admin, ana):
    terminada = partida(db_session, EstadoPartida.finalizada, (ana, 10))

    cerrar = client.post(f"/admin/partidas/{terminada.id}/cerrar", headers=con_token(admin))
    no_existe = client.post("/admin/partidas/9999/cerrar", headers=con_token(admin))

    assert cerrar.status_code == 409
    assert no_existe.status_code == 404


# script para crear la cuenta de administrador


def test_el_script_crea_la_cuenta_de_administrador_verificada(db_session):
    repo = UsuarioRepository(db_session)

    admin = crear_admin.crear_admin(repo, "jefe", "jefe@mail.com", "Secreta123")

    assert admin.rol == ROL_ADMIN and admin.correo_verificado


def test_el_script_promueve_una_cuenta_que_ya_existe(db_session, ana):
    repo = UsuarioRepository(db_session)

    admin = crear_admin.crear_admin(repo, "ana", "ana@mail.com", "Secreta123")

    assert admin.id == ana.id and admin.rol == ROL_ADMIN


def test_el_script_rechaza_una_contrasena_debil(monkeypatch, capsys):
    monkeypatch.setenv("ADMIN_CONTRASENA", "solotexto")

    assert crear_admin.main(["--usuario", "jefe", "--correo", "jefe@mail.com"]) == 1
    assert "letra y un número" in capsys.readouterr().out


def test_una_cuenta_bloqueada_tampoco_entra_con_google(db_session, ana):
    ana.google_id = "g-ana"
    ana.correo_verificado = True
    ana.bloqueado = True
    UsuarioRepository(db_session).guardar(ana)
    perfil = PerfilGoogle(google_id="g-ana", correo="ana@mail.com", correo_verificado=True)

    with pytest.raises(CuentaBloqueadaError):
        LoginSocialService(UsuarioRepository(db_session)).entrar_con_google(perfil)
