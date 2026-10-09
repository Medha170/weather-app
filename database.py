import sqlite3
from contextlib import closing
from datetime import datetime, timezone


def connect(database):
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(database):
    with closing(connect(database)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                location TEXT NOT NULL,
                searched_at TEXT NOT NULL
            )
            """
        )


def add_search(database, city, location):
    searched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO search_history (city, location, searched_at) VALUES (?, ?, ?)",
            (city, location, searched_at),
        )


def get_recent_searches(database, limit=5):
    with closing(connect(database)) as connection, connection:
        rows = connection.execute(
            """
            SELECT city, location, searched_at
            FROM search_history
            ORDER BY searched_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
