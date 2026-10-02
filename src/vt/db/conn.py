import os
import psycopg


def connect():
    # prepare_threshold=None: compatible con el pooler de Supabase en modo transacción.
    return psycopg.connect(os.environ["DATABASE_URL"], prepare_threshold=None)
