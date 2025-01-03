import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db():
    connection = sqlite3.connect(':memory')
    try:
        yield connection
    finally:
        connection.close()
