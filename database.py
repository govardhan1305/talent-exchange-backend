import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "talent_exchange.db"
)


def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


def init_database():

    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            skill TEXT DEFAULT '',

            learning_skill TEXT DEFAULT '',

            bio TEXT DEFAULT '',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    connection.commit()

    connection.close()


if __name__ == "__main__":

    init_database()

    print("Talent Exchange database initialized successfully.")
