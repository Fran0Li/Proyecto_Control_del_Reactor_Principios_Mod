from datetime import UTC, datetime


def ahora_utc() -> datetime:
    # sin zona horaria, igual que las columnas DateTime de la base de datos
    return datetime.now(UTC).replace(tzinfo=None)
