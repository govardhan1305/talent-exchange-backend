import sqlite3
import os


# ==========================================
# DATABASE PATH
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "talent_exchange.db"
)


# ==========================================
# GET CONNECTION
# ==========================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_database():

    connection = get_connection()

    # USERS TABLE
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


    # EXCHANGE REQUESTS TABLE
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS exchange_requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender_id INTEGER NOT NULL,

            receiver_id INTEGER NOT NULL,

            skill TEXT NOT NULL,

            status TEXT DEFAULT 'pending',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(sender_id)
                REFERENCES users(id),

            FOREIGN KEY(receiver_id)
                REFERENCES users(id)

        )
        """
    )


    connection.commit()

    connection.close()


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    init_database()

    print(
        "Talent Exchange database initialized successfully."
    )
