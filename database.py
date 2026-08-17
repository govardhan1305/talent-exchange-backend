import os
import psycopg
from psycopg.rows import dict_row


# ==========================================
# DATABASE URL
# ==========================================

DATABASE_URL = os.environ.get("DATABASE_URL")


# ==========================================
# GET CONNECTION
# ==========================================

def get_connection():

    if not DATABASE_URL:

        raise Exception(
            "DATABASE_URL environment variable is missing."
        )

    connection = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )

    return connection


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_database():

    connection = get_connection()

    with connection.cursor() as cursor:

        # ======================================
        # USERS
        # ======================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id SERIAL PRIMARY KEY,

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
        # REQUESTS
        # ======================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (

                id SERIAL PRIMARY KEY,

                sender_id INTEGER NOT NULL,

                receiver_id INTEGER NOT NULL,

                skill TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'pending',

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (sender_id)
                    REFERENCES users(id),

                FOREIGN KEY (receiver_id)
                    REFERENCES users(id)

            )
            """
        )


        # ======================================
        # MESSAGES
        # ======================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (

                id SERIAL PRIMARY KEY,

                sender_id INTEGER NOT NULL,

                receiver_id INTEGER NOT NULL,

                message TEXT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (sender_id)
                    REFERENCES users(id),

                FOREIGN KEY (receiver_id)
                    REFERENCES users(id)

            )
            """
        )


        # ======================================
        # INDEXES
        # ======================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_requests_sender
            ON requests(sender_id)
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_requests_receiver
            ON requests(receiver_id)
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_sender_receiver
            ON messages(sender_id, receiver_id)
            """
        )


    connection.commit()
    connection.close()
