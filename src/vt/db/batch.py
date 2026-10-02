class Batch:
    """Acumula filas y las envía en lotes (executemany en modo pipeline): mucho más rápido que fila a fila."""
    def __init__(self, conn, sql, size=500):
        self.conn, self.sql, self.size, self.rows = conn, sql, size, []

    def add(self, row):
        self.rows.append(row)
        if len(self.rows) >= self.size:
            self.flush()

    def flush(self):
        if self.rows:
            with self.conn.cursor() as cur:
                cur.executemany(self.sql, self.rows)
            self.rows = []
