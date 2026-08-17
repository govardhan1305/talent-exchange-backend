import os

from flask import Flask, request, jsonify
from flask_cors import CORS

import psycopg
from psycopg.rows import dict_row

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


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
        raise Exception(
            "DATABASE_URL is missing in Render Environment."
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            # =================================================
            # USERS
            # =================================================

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


            # =================================================
            # REQUESTS
            # =================================================

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
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE

                )
                """
            )


            # =================================================
            # MESSAGES
            # =================================================

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
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE

                )
                """
            )


            # =================================================
            # CONNECTIONS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS connections (

                    id SERIAL PRIMARY KEY,

                    user1_id INTEGER NOT NULL,

                    user2_id INTEGER NOT NULL,

                    created_at TIMESTAMP
                        DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user1_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (user2_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    UNIQUE(user1_id, user2_id)

                )
                """
            )


            # =================================================
            # INDEXES
            # =================================================

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_users_email
                ON users(email)
                """
            )


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
                idx_messages_users
                ON messages(sender_id, receiver_id)
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_connections_user1
                ON connections(user1_id)
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_connections_user2
                ON connections(user2_id)
                """
            )


        connection.commit()

    except Exception as e:

        print(
            "DATABASE INITIALIZATION ERROR:",
            repr(e)
        )

        if connection:
            connection.rollback()

        raise

    finally:

        if connection:
            connection.close()


# =========================================================
# HOME
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({

        "success": True,

        "message":
        "Talent Exchange Python Backend is running!"

    })


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health", methods=["GET"])
def health():

    connection = None

    try:

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT 1"
            )

            cursor.fetchone()


        return jsonify({

            "success": True,

            "database":
            "connected"

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "database":
            "error",

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# SIGNUP
# =========================================================

@app.route("/api/signup", methods=["POST"])
def signup():

    connection = None

    try:

        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "success": False,

                "message":
                "Invalid JSON data."

            }), 400


        name = str(
            data.get(
                "name",
                ""
            )
        ).strip()


        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()


        password = str(
            data.get(
                "password",
                ""
            )
        )


        skill = str(
            data.get(
                "skill",
                ""
            )
        ).strip()


        learning_skill = str(
            data.get(
                "learning_skill",
                ""
            )
        ).strip()


        bio = str(
            data.get(
                "bio",
                ""
            )
        ).strip()


        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        if not name:

            return jsonify({

                "success": False,

                "message":
                "Name is required."

            }), 400


        if not email:

            return jsonify({

                "success": False,

                "message":
                "Email is required."

            }), 400


        if not password:

            return jsonify({

                "success": False,

                "message":
                "Password is required."

            }), 400


        if not skill:

            return jsonify({

                "success": False,

                "message":
                "Skill is required."

            }), 400


        if len(password) < 6:

            return jsonify({

                "success": False,

                "message":
                "Password must contain at least 6 characters."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

            # -------------------------------------------------
            # CHECK EMAIL
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(email) = %s
                """,
                (email,)
            )


            existing = cursor.fetchone()


            if existing:

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Email already registered. Please login."

                }), 409


            # -------------------------------------------------
            # HASH PASSWORD
            # -------------------------------------------------

            hashed_password = generate_password_hash(
                password
            )


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

                RETURNING
                    id,
                    name,
                    email,
                    skill,
                    learning_skill,
                    bio
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

            "message":
            "Account created successfully!",

            "user":
            new_user

        }), 201


    except psycopg.errors.UniqueViolation:

        if connection:
            connection.rollback()


        return jsonify({

            "success": False,

            "message":
            "Email already registered. Please login."

        }), 409


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "SIGNUP ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Signup failed: " +
            str(e)

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

        data = request.get_json(
            silent=True
        )


        if not data:

            return jsonify({

                "success": False,

                "message":
                "Invalid JSON data."

            }), 400


        email = str(
            data.get(
                "email",
                ""
            )
        ).strip().lower()


        password = str(
            data.get(
                "password",
                ""
            )
        )


        if not email or not password:

            return jsonify({

                "success": False,

                "message":
                "Email and password are required."

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

                    "message":
                    "Account not found. Please register first."

                }), 401


            stored_password = user["password"]


            password_correct = False


            # -------------------------------------------------
            # HASHED PASSWORD
            # -------------------------------------------------

            if (
                stored_password.startswith("pbkdf2:")
                or
                stored_password.startswith("scrypt:")
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

                    "message":
                    "Incorrect password."

                }), 401


            user.pop(
                "password",
                None
            )


            return jsonify({

                "success": True,

                "message":
                "Login successful!",

                "user":
                user

            })


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "LOGIN ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Login failed: " +
            str(e)

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

            "users":
            users

        })


    except Exception as e:

        print(
            "USERS ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET SINGLE USER
# =========================================================

@app.route(
    "/api/users/<int:user_id>",
    methods=["GET"]
)
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

                "message":
                "User not found."

            }), 404


        return jsonify({

            "success": True,

            "user":
            user

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# CREATE REQUEST
# =========================================================

@app.route(
    "/api/requests",
    methods=["POST"]
)
def create_request():

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}


        sender_id = data.get(
            "sender_id"
        )


        receiver_id = data.get(
            "receiver_id"
        )


        skill = str(
            data.get(
                "skill",
                ""
            )
        ).strip()


        if (
            sender_id is None
            or
            receiver_id is None
            or
            not skill
        ):

            return jsonify({

                "success": False,

                "message":
                "sender_id, receiver_id and skill are required."

            }), 400


        sender_id = int(sender_id)

        receiver_id = int(receiver_id)


        if sender_id == receiver_id:

            return jsonify({

                "success": False,

                "message":
                "You cannot send a request to yourself."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

            # -------------------------------------------------
            # CHECK SENDER
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE id = %s
                """,
                (sender_id,)
            )


            sender = cursor.fetchone()


            if not sender:

                return jsonify({

                    "success": False,

                    "message":
                    "Sender not found."

                }), 404


            # -------------------------------------------------
            # CHECK RECEIVER
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE id = %s
                """,
                (receiver_id,)
            )


            receiver = cursor.fetchone()


            if not receiver:

                return jsonify({

                    "success": False,

                    "message":
                    "Receiver not found."

                }), 404


            # -------------------------------------------------
            # CHECK EXISTING PENDING REQUEST
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM requests

                WHERE sender_id = %s
                AND receiver_id = %s
                AND status = 'pending'
                """,

                (
                    sender_id,
                    receiver_id
                )
            )


            existing = cursor.fetchone()


            if existing:

                return jsonify({

                    "success": False,

                    "message":
                    "Request already sent.",

                    "request_id":
                    existing["id"]

                }), 409


            # -------------------------------------------------
            # CHECK REVERSE PENDING REQUEST
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT id
                FROM requests

                WHERE sender_id = %s
                AND receiver_id = %s
                AND status = 'pending'
                """,

                (
                    receiver_id,
                    sender_id
                )
            )


            reverse_request = cursor.fetchone()


            if reverse_request:

                return jsonify({

                    "success": False,

                    "message":
                    "This user has already sent you a request.",

                    "request_id":
                    reverse_request["id"]

                }), 409


            # -------------------------------------------------
            # CREATE REQUEST
            # -------------------------------------------------

            cursor.execute(
                """
                INSERT INTO requests
                (
                    sender_id,
                    receiver_id,
                    skill,
                    status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'pending'
                )

                RETURNING
                    id,
                    sender_id,
                    receiver_id,
                    skill,
                    status,
                    created_at
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

            "message":
            "Request sent successfully!",

            "request":
            new_request

        }), 201


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "CREATE REQUEST ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Request failed: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET RECEIVED REQUESTS
# =========================================================

@app.route(
    "/api/requests/received/<int:user_id>",
    methods=["GET"]
)
def get_received_requests(user_id):

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

                    u.name AS sender_name,

                    u.email AS sender_email,

                    u.skill AS sender_skill,

                    u.learning_skill AS sender_learning_skill,

                    u.bio AS sender_bio

                FROM requests r

                JOIN users u
                    ON u.id = r.sender_id

                WHERE r.receiver_id = %s

                ORDER BY r.id DESC
                """,

                (user_id,)
            )


            requests = cursor.fetchall()


        return jsonify({

            "success": True,

            "requests":
            requests

        })


    except Exception as e:

        print(
            "RECEIVED REQUESTS ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET SENT REQUESTS
# =========================================================

@app.route(
    "/api/requests/sent/<int:user_id>",
    methods=["GET"]
)
def get_sent_requests(user_id):

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

                    u.name AS receiver_name,

                    u.email AS receiver_email,

                    u.skill AS receiver_skill,

                    u.learning_skill AS receiver_learning_skill,

                    u.bio AS receiver_bio

                FROM requests r

                JOIN users u
                    ON u.id = r.receiver_id

                WHERE r.sender_id = %s

                ORDER BY r.id DESC
                """,

                (user_id,)
            )


            requests = cursor.fetchall()


        return jsonify({

            "success": True,

            "requests":
            requests

        })


    except Exception as e:

        print(
            "SENT REQUESTS ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET ALL REQUESTS FOR USER
# =========================================================

@app.route(
    "/api/requests/user/<int:user_id>",
    methods=["GET"]
)
def get_user_requests(user_id):

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

                    sender.name AS sender_name,

                    sender.email AS sender_email,

                    receiver.name AS receiver_name,

                    receiver.email AS receiver_email

                FROM requests r

                JOIN users sender
                    ON sender.id = r.sender_id

                JOIN users receiver
                    ON receiver.id = r.receiver_id

                WHERE
                    r.sender_id = %s
                    OR
                    r.receiver_id = %s

                ORDER BY r.id DESC
                """,

                (
                    user_id,
                    user_id
                )
            )


            requests = cursor.fetchall()


        return jsonify({

            "success": True,

            "requests":
            requests

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET ONE REQUEST
# =========================================================

@app.route(
    "/api/requests/<int:request_id>",
    methods=["GET"]
)
def get_request(request_id):

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

                    sender.name AS sender_name,

                    sender.email AS sender_email,

                    receiver.name AS receiver_name,

                    receiver.email AS receiver_email

                FROM requests r

                JOIN users sender
                    ON sender.id = r.sender_id

                JOIN users receiver
                    ON receiver.id = r.receiver_id

                WHERE r.id = %s
                """,

                (request_id,)
            )


            result = cursor.fetchone()


        if not result:

            return jsonify({

                "success": False,

                "message":
                "Request not found."

            }), 404


        return jsonify({

            "success": True,

            "request":
            result

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# ACCEPT REQUEST
# =========================================================
#
# IMPORTANT:
#
# Frontend only needs to send:
#
# POST /api/requests/<REQUEST_ID>/accept
#
# The backend finds the real sender and receiver from
# the request itself.
#
# This fixes the Rahul -> Accept problem.
#
# =========================================================

@app.route(
    "/api/requests/<int:request_id>/accept",
    methods=["POST", "PUT"]
)
def accept_request(request_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            # -------------------------------------------------
            # FIND REQUEST
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT

                    id,

                    sender_id,

                    receiver_id,

                    skill,

                    status,

                    created_at

                FROM requests

                WHERE id = %s

                FOR UPDATE
                """,

                (request_id,)
            )


            req = cursor.fetchone()


            if not req:

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Request not found."

                }), 404


            sender_id = int(
                req["sender_id"]
            )


            receiver_id = int(
                req["receiver_id"]
            )


            # -------------------------------------------------
            # ALREADY ACCEPTED
            # -------------------------------------------------

            if req["status"] == "accepted":

                # Make sure connection exists

                user1 = min(
                    sender_id,
                    receiver_id
                )

                user2 = max(
                    sender_id,
                    receiver_id
                )


                cursor.execute(
                    """
                    INSERT INTO connections
                    (
                        user1_id,
                        user2_id
                    )

                    VALUES
                    (
                        %s,
                        %s
                    )

                    ON CONFLICT
                    (user1_id, user2_id)
                    DO NOTHING
                    """,

                    (
                        user1,
                        user2
                    )
                )


                connection.commit()


                cursor.execute(
                    """
                    SELECT
                        id,
                        user1_id,
                        user2_id,
                        created_at

                    FROM connections

                    WHERE user1_id = %s
                    AND user2_id = %s
                    """,

                    (
                        user1,
                        user2
                    )
                )


                connection_data = cursor.fetchone()


                return jsonify({

                    "success": True,

                    "message":
                    "Request was already accepted.",

                    "request_id":
                    request_id,

                    "status":
                    "accepted",

                    "connection":
                    connection_data

                })


            # -------------------------------------------------
            # ONLY PENDING CAN BE ACCEPTED
            # -------------------------------------------------

            if req["status"] != "pending":

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Request is already " +
                    str(req["status"]) +
                    "."

                }), 409


            # -------------------------------------------------
            # UPDATE REQUEST
            # -------------------------------------------------

            cursor.execute(
                """
                UPDATE requests

                SET status = 'accepted'

                WHERE id = %s

                RETURNING
                    id,
                    sender_id,
                    receiver_id,
                    skill,
                    status,
                    created_at
                """,

                (request_id,)
            )


            updated_request = cursor.fetchone()


            # -------------------------------------------------
            # CREATE CONNECTION
            # -------------------------------------------------

            user1 = min(
                sender_id,
                receiver_id
            )


            user2 = max(
                sender_id,
                receiver_id
            )


            cursor.execute(
                """
                INSERT INTO connections
                (
                    user1_id,
                    user2_id
                )

                VALUES
                (
                    %s,
                    %s
                )

                ON CONFLICT
                (user1_id, user2_id)
                DO NOTHING
                """,

                (
                    user1,
                    user2
                )
            )


            # -------------------------------------------------
            # GET CONNECTION
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT

                    id,

                    user1_id,

                    user2_id,

                    created_at

                FROM connections

                WHERE user1_id = %s

                AND user2_id = %s
                """,

                (
                    user1,
                    user2
                )
            )


            connection_data = cursor.fetchone()


            # -------------------------------------------------
            # GET USERS
            # -------------------------------------------------

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

                WHERE id IN (%s, %s)

                ORDER BY id
                """,

                (
                    sender_id,
                    receiver_id
                )
            )


            users = cursor.fetchall()


        # -----------------------------------------------------
        # COMMIT EVERYTHING
        # -----------------------------------------------------

        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Request accepted successfully!",

            "request":
            updated_request,

            "connection":
            connection_data,

            "users":
            users

        })


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "ACCEPT REQUEST ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Accept request failed: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# REJECT REQUEST
# =========================================================

@app.route(
    "/api/requests/<int:request_id>/reject",
    methods=["POST", "PUT"]
)
def reject_request(request_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    status

                FROM requests

                WHERE id = %s

                FOR UPDATE
                """,

                (request_id,)
            )


            req = cursor.fetchone()


            if not req:

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Request not found."

                }), 404


            if req["status"] != "pending":

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Request is already " +
                    str(req["status"]) +
                    "."

                }), 409


            cursor.execute(
                """
                UPDATE requests

                SET status = 'rejected'

                WHERE id = %s

                RETURNING
                    id,
                    sender_id,
                    receiver_id,
                    skill,
                    status,
                    created_at
                """,

                (request_id,)
            )


            updated_request = cursor.fetchone()


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Request rejected successfully!",

            "request":
            updated_request

        })


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "REJECT REQUEST ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Reject request failed: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# DELETE / CANCEL REQUEST
# =========================================================

@app.route(
    "/api/requests/<int:request_id>",
    methods=["DELETE"]
)
def delete_request(request_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM requests

                WHERE id = %s

                RETURNING id
                """,

                (request_id,)
            )


            deleted = cursor.fetchone()


        if not deleted:

            connection.rollback()

            return jsonify({

                "success": False,

                "message":
                "Request not found."

            }), 404


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Request deleted successfully."

        })


    except Exception as e:

        if connection:
            connection.rollback()


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET CONNECTIONS
# =========================================================

@app.route(
    "/api/connections/<int:user_id>",
    methods=["GET"]
)
def get_connections(user_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT

                    c.id,

                    c.user1_id,

                    c.user2_id,

                    c.created_at,

                    u1.name AS user1_name,

                    u1.email AS user1_email,

                    u1.skill AS user1_skill,

                    u1.learning_skill AS user1_learning_skill,

                    u2.name AS user2_name,

                    u2.email AS user2_email,

                    u2.skill AS user2_skill,

                    u2.learning_skill AS user2_learning_skill

                FROM connections c

                JOIN users u1
                    ON u1.id = c.user1_id

                JOIN users u2
                    ON u2.id = c.user2_id

                WHERE
                    c.user1_id = %s
                    OR
                    c.user2_id = %s

                ORDER BY c.id DESC
                """,

                (
                    user_id,
                    user_id
                )
            )


            rows = cursor.fetchall()


        connections = []


        for row in rows:

            if row["user1_id"] == user_id:

                other_id = row["user2_id"]

                other_name = row["user2_name"]

                other_email = row["user2_email"]

                other_skill = row["user2_skill"]

                other_learning_skill = (
                    row["user2_learning_skill"]
                )

            else:

                other_id = row["user1_id"]

                other_name = row["user1_name"]

                other_email = row["user1_email"]

                other_skill = row["user1_skill"]

                other_learning_skill = (
                    row["user1_learning_skill"]
                )


            connections.append({

                "id":
                row["id"],

                "user_id":
                user_id,

                "other_user_id":
                other_id,

                "name":
                other_name,

                "email":
                other_email,

                "skill":
                other_skill,

                "learning_skill":
                other_learning_skill,

                "created_at":
                row["created_at"]

            })


        return jsonify({

            "success": True,

            "connections":
            connections

        })


    except Exception as e:

        print(
            "CONNECTIONS ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# CHECK CONNECTION
# =========================================================

@app.route(
    "/api/connections/check",
    methods=["GET"]
)
def check_connection():

    connection = None

    try:

        user1_id = request.args.get(
            "user1_id"
        )

        user2_id = request.args.get(
            "user2_id"
        )


        if not user1_id or not user2_id:

            return jsonify({

                "success": False,

                "message":
                "user1_id and user2_id are required."

            }), 400


        user1_id = int(user1_id)

        user2_id = int(user2_id)


        user1 = min(
            user1_id,
            user2_id
        )


        user2 = max(
            user1_id,
            user2_id
        )


        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT

                    id,

                    user1_id,

                    user2_id,

                    created_at

                FROM connections

                WHERE user1_id = %s

                AND user2_id = %s
                """,

                (
                    user1,
                    user2
                )
            )


            result = cursor.fetchone()


        return jsonify({

            "success": True,

            "connected":
            result is not None,

            "connection":
            result

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# SEND MESSAGE
# =========================================================

@app.route(
    "/api/messages",
    methods=["POST"]
)
def send_message():

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}


        sender_id = data.get(
            "sender_id"
        )


        receiver_id = data.get(
            "receiver_id"
        )


        message = str(
            data.get(
                "message",
                ""
            )
        ).strip()


        if (
            sender_id is None
            or
            receiver_id is None
            or
            not message
        ):

            return jsonify({

                "success": False,

                "message":
                "sender_id, receiver_id and message are required."

            }), 400


        sender_id = int(sender_id)

        receiver_id = int(receiver_id)


        connection = get_connection()


        with connection.cursor() as cursor:

            # -------------------------------------------------
            # CHECK CONNECTION
            # -------------------------------------------------

            user1 = min(
                sender_id,
                receiver_id
            )

            user2 = max(
                sender_id,
                receiver_id
            )


            cursor.execute(
                """
                SELECT id

                FROM connections

                WHERE user1_id = %s

                AND user2_id = %s
                """,

                (
                    user1,
                    user2
                )
            )


            connected = cursor.fetchone()


            if not connected:

                return jsonify({

                    "success": False,

                    "message":
                    "Users are not connected."

                }), 403


            # -------------------------------------------------
            # INSERT MESSAGE
            # -------------------------------------------------

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

                RETURNING
                    id,
                    sender_id,
                    receiver_id,
                    message,
                    created_at
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

            "message":
            new_message

        }), 201


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "SEND MESSAGE ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Message failed: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET MESSAGES
# =========================================================

@app.route(
    "/api/messages/<int:user1_id>/<int:user2_id>",
    methods=["GET"]
)
def get_messages(user1_id, user2_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT

                    m.id,

                    m.sender_id,

                    m.receiver_id,

                    m.message,

                    m.created_at,

                    sender.name AS sender_name,

                    receiver.name AS receiver_name

                FROM messages m

                JOIN users sender
                    ON sender.id = m.sender_id

                JOIN users receiver
                    ON receiver.id = m.receiver_id

                WHERE

                    (
                        m.sender_id = %s
                        AND
                        m.receiver_id = %s
                    )

                    OR

                    (
                        m.sender_id = %s
                        AND
                        m.receiver_id = %s
                    )

                ORDER BY m.id ASC
                """,

                (
                    user1_id,
                    user2_id,
                    user2_id,
                    user1_id
                )
            )


            messages = cursor.fetchall()


        return jsonify({

            "success": True,

            "messages":
            messages

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# DELETE USER
# =========================================================

@app.route(
    "/api/users/<int:user_id>",
    methods=["DELETE"]
)
def delete_user(user_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM users

                WHERE id = %s

                RETURNING id
                """,

                (user_id,)
            )


            deleted = cursor.fetchone()


        if not deleted:

            connection.rollback()

            return jsonify({

                "success": False,

                "message":
                "User not found."

            }), 404


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "User deleted successfully."

        })


    except Exception as e:

        if connection:
            connection.rollback()


        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def not_found(error):

    return jsonify({

        "success": False,

        "message":
        "API endpoint not found."

    }), 404


@app.errorhandler(405)
def method_not_allowed(error):

    return jsonify({

        "success": False,

        "message":
        "HTTP method not allowed."

    }), 405


@app.errorhandler(500)
def internal_error(error):

    return jsonify({

        "success": False,

        "message":
        "Internal server error."

    }), 500


# =========================================================
# STARTUP
# =========================================================

try:

    init_database()

    print(
        "DATABASE INITIALIZED SUCCESSFULLY"
    )

except Exception as e:

    print(
        "DATABASE STARTUP ERROR:",
        repr(e)
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
