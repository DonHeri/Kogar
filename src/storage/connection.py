import psycopg2


class DatabaseConnection:
    def __init__(self, host, port, database, user, password) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None

    def __enter__(self):
        self.conn = psycopg2.connect(
            database=self.database,
            user=self.user,
            host=self.host,
            password=self.password,
            port=self.port,
        )
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                # no hubo excepción
                self.conn.commit()
            else:
                # hubo excepción
                self.conn.rollback()
        finally:
            self.conn.close()
