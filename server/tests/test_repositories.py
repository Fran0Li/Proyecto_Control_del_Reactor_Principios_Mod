from app.models.partida import EstadoPartida, Partida
from app.models.usuario import Usuario
from app.repositories import PartidaRepository, UsuarioRepository


def crear_usuario(repo, nombre="julian", correo="julian@mail.com"):
    usuario = Usuario(nombre_usuario=nombre, correo=correo, contrasena_hash="hash")
    return repo.crear(usuario)


def test_crear_y_buscar_usuario_por_correo(db_session):
    repo = UsuarioRepository(db_session)
    creado = crear_usuario(repo)

    assert creado.id is not None
    assert repo.obtener_por_correo("julian@mail.com").id == creado.id


def test_existe_correo_y_nombre_usuario(db_session):
    repo = UsuarioRepository(db_session)
    crear_usuario(repo)

    assert repo.existe_correo("julian@mail.com")
    assert repo.existe_nombre_usuario("julian")
    assert not repo.existe_correo("otro@mail.com")


def test_usuario_inexistente_devuelve_none(db_session):
    repo = UsuarioRepository(db_session)

    assert repo.obtener_por_id(999) is None
    assert repo.obtener_por_correo("nadie@mail.com") is None


def test_partida_nueva_queda_en_esperando(db_session):
    repo = PartidaRepository(db_session)
    partida = repo.crear(Partida())

    assert partida.id is not None
    assert partida.estado == EstadoPartida.esperando


def test_listar_disponibles_solo_incluye_esperando(db_session):
    repo = PartidaRepository(db_session)
    esperando = repo.crear(Partida())
    en_curso = repo.crear(Partida())
    repo.cambiar_estado(en_curso, EstadoPartida.en_curso)

    ids = [p.id for p in repo.listar_disponibles()]

    assert esperando.id in ids
    assert en_curso.id not in ids


def test_agregar_participante_y_contar(db_session):
    usuarios = UsuarioRepository(db_session)
    partidas = PartidaRepository(db_session)
    partida = partidas.crear(Partida())
    ana = crear_usuario(usuarios, "ana", "ana@mail.com")
    beto = crear_usuario(usuarios, "beto", "beto@mail.com")

    partidas.agregar_participante(partida.id, ana.id)
    partidas.agregar_participante(partida.id, beto.id)

    assert partidas.contar_participantes(partida.id) == 2
    assert len(partidas.listar_participaciones(partida.id)) == 2


def test_cambiar_estado_registra_fechas(db_session):
    repo = PartidaRepository(db_session)
    partida = repo.crear(Partida())

    repo.cambiar_estado(partida, EstadoPartida.en_curso)
    assert partida.fecha_inicio is not None

    repo.cambiar_estado(partida, EstadoPartida.finalizada)
    assert partida.fecha_fin is not None


def test_jugador_en_partida_activa_rn04(db_session):
    usuarios = UsuarioRepository(db_session)
    partidas = PartidaRepository(db_session)
    jugador = crear_usuario(usuarios)
    partida = partidas.crear(Partida())

    assert not partidas.jugador_en_partida_activa(jugador.id)

    partidas.agregar_participante(partida.id, jugador.id)
    assert partidas.jugador_en_partida_activa(jugador.id)

    partidas.cambiar_estado(partida, EstadoPartida.finalizada)
    assert not partidas.jugador_en_partida_activa(jugador.id)