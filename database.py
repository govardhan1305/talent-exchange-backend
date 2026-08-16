import sqlite3


# ==========================================
# DATABASE FILE
# ==========================================

DATABASE_NAME = "talent_exchange.db"


# ==========================================
# GET CONNECTION
# ==========================================

def get_connection():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_database():

    connection = get_connection()


    # ======================================
    # USERS TABLE
    # ======================================

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password TEXT NOT NULL,

            skill TEXT DEFAULT '',

            learning_skill TEXT DEFAULT '',

            bio TEXT DEFAULT ''

        )
        """
    )


    # ======================================
    # REQUESTS TABLE
    # ======================================

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender_id INTEGER NOT NULL,

            receiver_id INTEGER NOT NULL,

            skill TEXT NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                sender_id
            )
            REFERENCES users(id),

            FOREIGN KEY (
                receiver_id
            )
            REFERENCES users(id)

        )
        """
    )


    # ======================================
    # MESSAGES TABLE
    # ======================================

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            sender_id INTEGER NOT NULL,

            receiver_id INTEGER NOT NULL,

            message TEXT NOT NULL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                sender_id
            )
            REFERENCES users(id),

            FOREIGN KEY (
                receiver_id
            )
            REFERENCES users(id)

        )
        """
    )


    # ======================================
    # REQUEST INDEXES
    # ======================================

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_requests_sender
        ON requests(sender_id)
        """
    )


    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_requests_receiver
        ON requests(receiver_id)
        """
    )


    # ======================================
    # MESSAGE INDEXES
    # ======================================

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_messages_sender
        ON messages(sender_id)
        """
    )


    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_messages_receiver
        ON messages(receiver_id)
        """
    )


    connection.commit()

    connection.close()
