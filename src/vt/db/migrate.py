"""Aplica db/migrations/*.sql en orden (idempotente). Imprime solo nombres de tablas."""
import glob
import os
from .conn import connect

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def main():
    with connect() as conn:
        conn.execute("create table if not exists schema_migrations (name text primary key, applied_at timestamptz default now())")
        done = {r[0] for r in conn.execute("select name from schema_migrations")}
        for path in sorted(glob.glob(os.path.join(ROOT, "db", "migrations", "*.sql"))):
            name = os.path.basename(path)
            if name in done:
                print("ya aplicada:", name)
                continue
            conn.execute(open(path, encoding="utf-8").read())
            conn.execute("insert into schema_migrations(name) values (%s)", (name,))
            print("aplicada:", name)
        conn.commit()
        tables = [r[0] for r in conn.execute(
            "select tablename from pg_tables where schemaname='public' order by 1")]
        print("tablas:", ", ".join(tables))


if __name__ == "__main__":
    main()
