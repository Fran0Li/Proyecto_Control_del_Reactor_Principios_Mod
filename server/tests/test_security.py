from app.core.security import ScryptPasswordHasher

# n bajo para que las pruebas corran rápido
hasher = ScryptPasswordHasher(n=2**10)


def test_el_hash_no_contiene_la_contrasena():
    hash_guardado = hasher.hash("Secreta123")

    assert "Secreta123" not in hash_guardado
    assert hash_guardado.startswith("scrypt$")


def test_verifica_la_contrasena_correcta():
    hash_guardado = hasher.hash("Secreta123")

    assert hasher.verificar("Secreta123", hash_guardado)


def test_rechaza_una_contrasena_incorrecta():
    hash_guardado = hasher.hash("Secreta123")

    assert not hasher.verificar("Secreta124", hash_guardado)


def test_la_misma_contrasena_genera_hashes_distintos():
    assert hasher.hash("Secreta123") != hasher.hash("Secreta123")


def test_un_hash_mal_formado_no_verifica():
    assert not hasher.verificar("Secreta123", "texto-cualquiera")
    assert not hasher.verificar("Secreta123", "bcrypt$1$2$3$aa$bb")
