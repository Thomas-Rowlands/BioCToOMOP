import psycopg
from contextlib import contextmanager


@contextmanager
def get_conn(
    host="localhost",
    port=5432,
    dbname="omop",
    user="omop_user",
    password="omop_pass",
):
    conn = psycopg.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
