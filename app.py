

import os

from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is missing in Render Environment.")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    connection = get_connection()

    try:

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # USERS
            # -------------------------------------------------

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

            # -------------------------------------------------
            # REQUESTS
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    skill TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (sender_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
                )
                """
            )

            # -------------------------------------------------
            # MESSAGES
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (sender_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
                )
                """
            )

            # -------------------------------------------------
            # INDEXES
            # -------------------------------------------------

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(email)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_requests_sender
                ON requests(sender_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_requests_receiver
                ON requests(receiver_id)
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_users
                ON messages(sender_id, receiver_id)
                """
            )

        connection.commit()

    finally:
        connection.close()


# =========================================================
# HOME / HEALTH CHECK
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "message": "Talent Exchange Python Backend is running!"
    })


@app.route("/api/health", methods=["GET"])
def health():

    try:

        connection = get_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        connection.close()

        return jsonify({
            "success": True,
            "database": "connected"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "database": "error",
            "message": str(e)
        }), 500


# =========================================================
# SIGNUP
# =========================================================

@app.route("/api/signup", methods=["POST"])
def signup():

    connection = None

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid JSON data."
            }), 400

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))
        skill = str(data.get("skill", "")).strip()

        learning_skill = str(
            data.get("learning_skill", "")
        ).strip()

        bio = str(
            data.get("bio", "")
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name:
            return jsonify({
                "success": False,
                "message": "Name is required."
            }), 400

        if not email:
            return jsonify({
                "success": False,
                "message": "Email is required."
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Password is required."
            }), 400

        if not skill:
            return jsonify({
                "success": False,
                "message": "Skill is required."
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must contain at least 6 characters."
            }), 400

        connection = get_connection()

        with connection.cursor() as cursor:

            # -------------------------------------------------
            # CHECK EXISTING USER
            # IMPORTANT: psycopg uses %s, NOT ?
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id, name, email
                FROM users
                WHERE LOWER(email) = %s
                """,
                (email,)
            )

            existing_user = cursor.fetchone()

            if existing_user:

                connection.rollback()

                return jsonify({
                    "success": False,
                    "message": "Email already registered. Please login."
                }), 409

            # -------------------------------------------------
            # HASH PASSWORD
            # -------------------------------------------------

            hashed_password = generate_password_hash(password)

            # -------------------------------------------------
            # CREATE USER
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    skill,
                    learning_skill,
                    bio
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING id, name, email, skill,
                          learning_skill, bio
                """,
                (
                    name,
                    email,
                    hashed_password,
                    skill,
                    learning_skill,
                    bio
                )
            )

            new_user = cursor.fetchone()

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully!",
            "user": new_user
        }), 201

    except psycopg.errors.UniqueViolation:

        if connection:
            connection.rollback()

        return jsonify({
            "success": False,
            "message": "Email already registered. Please login."
        }), 409

    except Exception as e:

        if connection:
            connection.rollback()

        print("SIGNUP ERROR:", repr(e))

        return jsonify({
            "success": False,
            "message": "Signup failed: " + str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# LOGIN
# =========================================================

@app.route("/api/login", methods=["POST"])
def login():

    connection = None

    try:

        data = request.get_json(silent=True)

        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid JSON data."
            }), 400

        email = str(
            data.get("email", "")
        ).strip().lower()

        password = str(
            data.get("password", "")
        )

        if not email or not password:

            return jsonify({
                "success": False,
                "message": "Email and password are required."
            }), 400

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    password,
                    skill,
                    learning_skill,
                    bio
                FROM users
                WHERE LOWER(email) = %s
                """,
                (email,)
            )

            user = cursor.fetchone()

            if not user:

                return jsonify({
                    "success": False,
                    "message": "Account not found. Please register first."
                }), 401

            stored_password = user["password"]

            password_correct = False

            # -------------------------------------------------
            # NEW HASHED PASSWORD
            # -------------------------------------------------

            if (
                stored_password.startswith("pbkdf2:")
                or stored_password.startswith("scrypt:")
            ):

                password_correct = check_password_hash(
                    stored_password,
                    password
                )

            # -------------------------------------------------
            # OLD PASSWORD COMPATIBILITY
            # -------------------------------------------------

            else:

                password_correct = (
                    stored_password == password
                )

                # Upgrade old password to secure hash
                if password_correct:

                    new_hash = generate_password_hash(
                        password
                    )

                    cursor.execute(
                        """
                        UPDATE users
                        SET password = %s
                        WHERE id = %s
                        """,
                        (
                            new_hash,
                            user["id"]
                        )
                    )

                    connection.commit()

            if not password_correct:

                return jsonify({
                    "success": False,
                    "message": "Incorrect password."
                }), 401

            # Don't send password to frontend
            user.pop("password", None)

            return jsonify({
                "success": True,
                "message": "Login successful!",
                "user": user
            }), 200

    except Exception as e:

        if connection:
            connection.rollback()

        print("LOGIN ERROR:", repr(e))

        return jsonify({
            "success": False,
            "message": "Login failed: " + str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# GET ALL USERS
# =========================================================

@app.route("/api/users", methods=["GET"])
def get_users():

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    skill,
                    learning_skill,
                    bio
                FROM users
                ORDER BY id DESC
                """
            )

            users = cursor.fetchall()

        return jsonify({
            "success": True,
            "users": users
        })

    except Exception as e:

        print("USERS ERROR:", repr(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# GET SINGLE USER
# =========================================================

@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    skill,
                    learning_skill,
                    bio
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )

            user = cursor.fetchone()

        if not user:

            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        return jsonify({
            "success": True,
            "user": user
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# CREATE SKILL REQUEST
# =========================================================

@app.route("/api/requests", methods=["POST"])
def create_request():

    connection = None

    try:

        data = request.get_json(silent=True) or {}

        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        skill = str(data.get("skill", "")).strip()

        if not sender_id or not receiver_id or not skill:

            return jsonify({
                "success": False,
                "message": "sender_id, receiver_id and skill are required."
            }), 400

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO requests
                (
                    sender_id,
                    receiver_id,
                    skill
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                RETURNING *
                """,
                (
                    sender_id,
                    receiver_id,
                    skill
                )
            )

            new_request = cursor.fetchone()

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Request sent successfully.",
            "request": new_request
        }), 201

    except Exception as e:

        if connection:
            connection.rollback()

        print("REQUEST ERROR:", repr(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# GET REQUESTS
# =========================================================

@app.route("/api/requests/<int:user_id>", methods=["GET"])
def get_requests(user_id):

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    r.id,
                    r.sender_id,
                    r.receiver_id,
                    r.skill,
                    r.status,
                    r.created_at,

                    s.name AS sender_name,
                    s.email AS sender_email,

                    rec.name AS receiver_name,
                    rec.email AS receiver_email

                FROM requests r

                JOIN users s
                    ON r.sender_id = s.id

                JOIN users rec
                    ON r.receiver_id = rec.id

                WHERE
                    r.sender_id = %s
                    OR r.receiver_id = %s

                ORDER BY r.created_at DESC
                """,
                (
                    user_id,
                    user_id
                )
            )

            requests = cursor.fetchall()

        return jsonify({
            "success": True,
            "requests": requests
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# SEND MESSAGE
# =========================================================

@app.route("/api/messages", methods=["POST"])
def send_message():

    connection = None

    try:

        data = request.get_json(silent=True) or {}

        sender_id = data.get("sender_id")
        receiver_id = data.get("receiver_id")
        message = str(data.get("message", "")).strip()

        if not sender_id or not receiver_id or not message:

            return jsonify({
                "success": False,
                "message": "sender_id, receiver_id and message are required."
            }), 400

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    message
                )
                VALUES
                (
                    %s,
                    %s,
                    %s
                )
                RETURNING *
                """,
                (
                    sender_id,
                    receiver_id,
                    message
                )
            )

            new_message = cursor.fetchone()

        connection.commit()

        return jsonify({
            "success": True,
            "message": new_message
        }), 201

    except Exception as e:

        if connection:
            connection.rollback()

        print("MESSAGE ERROR:", repr(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# GET CHAT
# =========================================================

@app.route(
    "/api/messages/<int:user1>/<int:user2>",
    methods=["GET"]
)
def get_messages(user1, user2):

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    sender_id,
                    receiver_id,
                    message,
                    created_at

                FROM messages

                WHERE
                    (
                        sender_id = %s
                        AND receiver_id = %s
                    )

                    OR

                    (
                        sender_id = %s
                        AND receiver_id = %s
                    )

                ORDER BY created_at ASC
                """,
                (
                    user1,
                    user2,
                    user2,
                    user1
                )
            )

            messages = cursor.fetchall()

        return jsonify({
            "success": True,
            "messages": messages
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:

        if connection:
            connection.close()


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    try:

        init_database()

        print("Database initialized successfully.")

    except Exception as e:

        print(
            "Database initialization failed:",
            repr(e)
        )

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
```
