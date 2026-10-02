import os


def connect():
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgres://")):
        # No se imprime el valor: puede contener la contraseña.
        raise SystemExit("DATABASE_URL no es una cadena de conexión Postgres (debe empezar por postgresql://). "
                         "En Supabase: Connect > Transaction pooler.")
    import psycopg                      # import tardío: los tests puros no lo necesitan
    # prepare_threshold=None: compatible con el pooler de Supabase en modo transacción.
    return psycopg.connect(url, prepare_threshold=None)
