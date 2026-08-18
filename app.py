import os
import time
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

import psycopg
from psycopg.rows import dict_row

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": "*"
        }
    }
)


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
            # SKILL EVIDENCE
            # =================================================
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_evidence (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_data BYTEA NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE
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


            # =================================================
            # CONNECTIONS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS connections (

                    id SERIAL PRIMARY KEY,

                    user1_id INTEGER NOT NULL,

                    user2_id INTEGER NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

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
            # WEBRTC SIGNALING
            # =================================================
            #
            # Stores temporary:
            #
            # offer
            # answer
            # ICE candidates
            #
            # The backend does NOT carry audio/video.
            #
            # WebRTC sends the actual media directly between
            # the browsers when possible.
            #
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS call_signals (

                    id SERIAL PRIMARY KEY,

                    caller_id INTEGER NOT NULL,

                    receiver_id INTEGER NOT NULL,

                    signal_type TEXT NOT NULL,

                    signal_data TEXT NOT NULL,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (caller_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE

                )
                """
            )


            # =================================================
            # CALL STATUS
            # =================================================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS calls (

                    id SERIAL PRIMARY KEY,

                    caller_id INTEGER NOT NULL,

                    receiver_id INTEGER NOT NULL,

                    call_type TEXT NOT NULL,

                    status TEXT NOT NULL DEFAULT 'ringing',

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (caller_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    FOREIGN KEY (receiver_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE

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


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_call_signals_receiver
                ON call_signals(receiver_id)
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_call_signals_pair
                ON call_signals(caller_id, receiver_id)
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_calls_receiver
                ON calls(receiver_id)
                """
            )


        connection.commit()

        print(
            "DATABASE INITIALIZED SUCCESSFULLY"
        )


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
        "Talent Exchange Python Backend is running!",

        "version":
        "2.0",

        "features": [
            "authentication",
            "users",
            "requests",
            "connections",
            "messages",
            "webrtc-signaling",
            "audio-calls",
            "video-calls"
        ]

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

        # Accept multipart/form-data from signup.html.
        name = str(request.form.get("name", "")).strip()
        email = str(request.form.get("email", "")).strip().lower()
        password = str(request.form.get("password", ""))
        skill = str(request.form.get("skill", "")).strip()
        learning_skill = str(request.form.get("learning_skill", "")).strip()
        bio = str(request.form.get("bio", "")).strip()
        evidence_file = request.files.get("skillEvidence")

        if not name:
            return jsonify({"success": False, "message": "Name is required."}), 400

        if not email:
            return jsonify({"success": False, "message": "Email is required."}), 400

        if not password:
            return jsonify({"success": False, "message": "Password is required."}), 400

        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must contain at least 6 characters."}), 400

        if not skill:
            return jsonify({"success": False, "message": "Skill is required."}), 400

        if not evidence_file or not evidence_file.filename:
            return jsonify({"success": False, "message": "Skill evidence is required."}), 400

        allowed_extensions = {"pdf", "jpg", "jpeg", "png", "mp4", "webm"}
        original_filename = secure_filename(evidence_file.filename)

        if "." not in original_filename:
            return jsonify({"success": False, "message": "Invalid file."}), 400

        extension = original_filename.rsplit(".", 1)[1].lower()

        if extension not in allowed_extensions:
            return jsonify({"success": False, "message": "Allowed files: PDF, JPG, PNG, MP4, WEBM."}), 400

        file_data = evidence_file.read()
        max_file_size = 10 * 1024 * 1024

        if len(file_data) == 0:
            return jsonify({"success": False, "message": "Uploaded file is empty."}), 400

        if len(file_data) > max_file_size:
            return jsonify({"success": False, "message": "File size must be 10 MB or less."}), 400

        file_type = evidence_file.mimetype or "application/octet-stream"

        connection = get_connection()

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT id FROM users WHERE LOWER(email) = %s",
                (email,)
            )
            existing = cursor.fetchone()

            if existing:
                connection.rollback()
                return jsonify({
                    "success": False,
                    "message": "Email already registered. Please login."
                }), 409

            hashed_password = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO users
                (name, email, password, skill, learning_skill, bio)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, name, email, skill, learning_skill, bio
                """,
                (
                    name, email, hashed_password,
                    skill, learning_skill, bio
                )
            )

            new_user = cursor.fetchone()

            stored_filename = (
                f"user_{new_user['id']}_{int(time.time())}.{extension}"
            )

            cursor.execute(
                """
                INSERT INTO skill_evidence
                (
                    user_id, original_filename, stored_filename,
                    file_type, file_data, status
                )
                VALUES (%s, %s, %s, %s, %s, 'pending')
                """,
                (
                    new_user["id"],
                    original_filename,
                    stored_filename,
                    file_type,
                    file_data
                )
            )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully. Skill evidence is pending admin verification.",
            "verification_status": "pending",
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


            if (
                stored_password.startswith("pbkdf2:")
                or
                stored_password.startswith("scrypt:")
            ):

                password_correct = check_password_hash(
                    stored_password,
                    password
                )


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

            # Check users

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE id IN (%s, %s)
                """,

                (
                    sender_id,
                    receiver_id
                )
            )


            users = cursor.fetchall()


            if len(users) != 2:

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Sender or receiver not found."

                }), 404


            # Check existing connection

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


            already_connected = cursor.fetchone()


            if already_connected:

                return jsonify({

                    "success": False,

                    "message":
                    "You are already connected with this user."

                }), 409


            # Check same pending request

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


            # Check reverse request

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
# RECEIVED REQUESTS
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
# SENT REQUESTS
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

        return jsonify({

            "success": False,

            "message":
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# ALL REQUESTS FOR USER
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

@app.route(
    "/api/requests/<int:request_id>/accept",
    methods=["POST", "PUT"]
)
def accept_request(request_id):

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


            user1 = min(
                sender_id,
                receiver_id
            )

            user2 = max(
                sender_id,
                receiver_id
            )


            if req["status"] == "accepted":

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


            elif req["status"] != "pending":

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Request is already " +
                    str(req["status"]) +
                    "."

                }), 409


            else:

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


                req = cursor.fetchone()


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


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Request accepted successfully!",

            "request":
            req,

            "connection":
            connection_data

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
# DELETE REQUEST
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


        if sender_id == receiver_id:

            return jsonify({

                "success": False,

                "message":
                "You cannot message yourself."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

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
# WEBRTC HELPER
# =========================================================

def verify_connection(
    user1_id,
    user2_id,
    cursor
):

    first = min(
        int(user1_id),
        int(user2_id)
    )

    second = max(
        int(user1_id),
        int(user2_id)
    )


    cursor.execute(
        """
        SELECT id

        FROM connections

        WHERE user1_id = %s

        AND user2_id = %s
        """,

        (
            first,
            second
        )
    )


    return cursor.fetchone() is not None


# =========================================================
# WEBRTC SEND SIGNAL
# =========================================================
#
# Frontend sends:
#
# {
#   "caller_id": 1,
#   "receiver_id": 2,
#   "signal_type": "offer",
#   "signal_data": "{...}"
# }
#
# signal_type can be:
#
# offer
# answer
# ice-candidate
# hangup
#
# =========================================================

@app.route(
    "/api/call/signal",
    methods=["POST"]
)
def send_call_signal():

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}


        caller_id = data.get(
            "caller_id"
        )

        receiver_id = data.get(
            "receiver_id"
        )

        signal_type = str(
            data.get(
                "signal_type",
                ""
            )
        ).strip().lower()


        signal_data = data.get(
            "signal_data"
        )


        if (
            caller_id is None
            or
            receiver_id is None
            or
            not signal_type
            or
            signal_data is None
        ):

            return jsonify({

                "success": False,

                "message":
                "caller_id, receiver_id, signal_type and signal_data are required."

            }), 400


        caller_id = int(
            caller_id
        )

        receiver_id = int(
            receiver_id
        )


        if caller_id == receiver_id:

            return jsonify({

                "success": False,

                "message":
                "You cannot call yourself."

            }), 400


        allowed_types = {

            "offer",
            "answer",
            "ice-candidate",
            "hangup"

        }


        if signal_type not in allowed_types:

            return jsonify({

                "success": False,

                "message":
                "Invalid signal_type."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

            connected = verify_connection(
                caller_id,
                receiver_id,
                cursor
            )


            if not connected:

                return jsonify({

                    "success": False,

                    "message":
                    "Users are not connected."

                }), 403


            # Convert object to JSON string if necessary

            if not isinstance(
                signal_data,
                str
            ):

                import json

                signal_data = json.dumps(
                    signal_data
                )


            cursor.execute(
                """
                INSERT INTO call_signals
                (
                    caller_id,
                    receiver_id,
                    signal_type,
                    signal_data
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )

                RETURNING

                    id,
                    caller_id,
                    receiver_id,
                    signal_type,
                    signal_data,
                    created_at
                """,

                (
                    caller_id,
                    receiver_id,
                    signal_type,
                    signal_data
                )
            )


            signal = cursor.fetchone()


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Call signal sent.",

            "signal":
            signal

        }), 201


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "SEND CALL SIGNAL ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Call signal failed: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET WEBRTC SIGNALS
# =========================================================
#
# Receiver asks:
#
# /api/call/signals/2
#
# The endpoint returns signals waiting for user 2.
#
# =========================================================

@app.route(
    "/api/call/signals/<int:user_id>",
    methods=["GET"]
)
def get_call_signals(user_id):

    connection = None

    try:

        after_id = request.args.get(
            "after_id",
            "0"
        )


        try:

            after_id = int(
                after_id
            )

        except:

            after_id = 0


        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT

                    id,
                    caller_id,
                    receiver_id,
                    signal_type,
                    signal_data,
                    created_at

                FROM call_signals

                WHERE receiver_id = %s

                AND id > %s

                ORDER BY id ASC

                LIMIT 100
                """,

                (
                    user_id,
                    after_id
                )
            )


            signals = cursor.fetchall()


        return jsonify({

            "success": True,

            "signals":
            signals

        })


    except Exception as e:

        print(
            "GET CALL SIGNALS ERROR:",
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
# DELETE OLD SIGNALS
# =========================================================

@app.route(
    "/api/call/signals/cleanup",
    methods=["POST"]
)
def cleanup_call_signals():

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM call_signals

                WHERE created_at <
                    CURRENT_TIMESTAMP - INTERVAL '10 minutes'
                """
            )


            deleted_count = cursor.rowcount


        connection.commit()


        return jsonify({

            "success": True,

            "deleted":
            deleted_count

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
# START CALL
# =========================================================
#
# call_type:
#
# audio
# video
#
# =========================================================

@app.route(
    "/api/call/start",
    methods=["POST"]
)
def start_call():

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}


        caller_id = data.get(
            "caller_id"
        )

        receiver_id = data.get(
            "receiver_id"
        )

        call_type = str(
            data.get(
                "call_type",
                "video"
            )
        ).strip().lower()


        if (
            caller_id is None
            or
            receiver_id is None
        ):

            return jsonify({

                "success": False,

                "message":
                "caller_id and receiver_id are required."

            }), 400


        caller_id = int(
            caller_id
        )

        receiver_id = int(
            receiver_id
        )


        if call_type not in (
            "audio",
            "video"
        ):

            return jsonify({

                "success": False,

                "message":
                "call_type must be audio or video."

            }), 400


        if caller_id == receiver_id:

            return jsonify({

                "success": False,

                "message":
                "You cannot call yourself."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

            connected = verify_connection(
                caller_id,
                receiver_id,
                cursor
            )


            if not connected:

                return jsonify({

                    "success": False,

                    "message":
                    "Users are not connected."

                }), 403


            # End old ringing calls between these users

            cursor.execute(
                """
                UPDATE calls

                SET status = 'ended'

                WHERE
                (
                    caller_id = %s
                    AND
                    receiver_id = %s
                )

                OR

                (
                    caller_id = %s
                    AND
                    receiver_id = %s
                )

                AND status = 'ringing'
                """,

                (
                    caller_id,
                    receiver_id,
                    receiver_id,
                    caller_id
                )
            )


            cursor.execute(
                """
                INSERT INTO calls
                (
                    caller_id,
                    receiver_id,
                    call_type,
                    status
                )

                VALUES
                (
                    %s,
                    %s,
                    %s,
                    'ringing'
                )

                RETURNING

                    id,
                    caller_id,
                    receiver_id,
                    call_type,
                    status,
                    created_at
                """,

                (
                    caller_id,
                    receiver_id,
                    call_type
                )
            )


            call = cursor.fetchone()


        connection.commit()


        return jsonify({

            "success": True,

            "message":
            "Call started.",

            "call":
            call

        }), 201


    except Exception as e:

        if connection:
            connection.rollback()


        print(
            "START CALL ERROR:",
            repr(e)
        )


        return jsonify({

            "success": False,

            "message":
            "Could not start call: " +
            str(e)

        }), 500


    finally:

        if connection:
            connection.close()


# =========================================================
# GET INCOMING CALLS
# =========================================================

@app.route(
    "/api/call/incoming/<int:user_id>",
    methods=["GET"]
)
def get_incoming_calls(user_id):

    connection = None

    try:

        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT

                    c.id,

                    c.caller_id,

                    c.receiver_id,

                    c.call_type,

                    c.status,

                    c.created_at,

                    u.name AS caller_name,

                    u.email AS caller_email

                FROM calls c

                JOIN users u
                    ON u.id = c.caller_id

                WHERE c.receiver_id = %s

                AND c.status = 'ringing'

                ORDER BY c.id DESC

                LIMIT 10
                """,

                (user_id,)
            )


            calls = cursor.fetchall()


        return jsonify({

            "success": True,

            "calls":
            calls

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
# UPDATE CALL STATUS
# =========================================================

@app.route(
    "/api/call/<int:call_id>/status",
    methods=["POST", "PUT"]
)
def update_call_status(call_id):

    connection = None

    try:

        data = request.get_json(
            silent=True
        ) or {}


        status = str(
            data.get(
                "status",
                ""
            )
        ).strip().lower()


        allowed_statuses = {

            "ringing",
            "accepted",
            "rejected",
            "ended",
            "busy"

        }


        if status not in allowed_statuses:

            return jsonify({

                "success": False,

                "message":
                "Invalid call status."

            }), 400


        connection = get_connection()


        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE calls

                SET status = %s

                WHERE id = %s

                RETURNING

                    id,
                    caller_id,
                    receiver_id,
                    call_type,
                    status,
                    created_at
                """,

                (
                    status,
                    call_id
                )
            )


            call = cursor.fetchone()


            if not call:

                connection.rollback()

                return jsonify({

                    "success": False,

                    "message":
                    "Call not found."

                }), 404


        connection.commit()


        return jsonify({

            "success": True,

            "call":
            call

        })


    except Exception as e:

        if connection:
            connection.rollback()


        return jsonify({

            "success": False,

            "message":
            "Call status update failed: " +
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
# PERIODIC SIGNAL CLEANUP
# =========================================================

def cleanup_loop():

    while True:

        try:

            connection = get_connection()

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    DELETE FROM call_signals

                    WHERE created_at <
                        CURRENT_TIMESTAMP - INTERVAL '10 minutes'
                    """
                )

            connection.commit()

            connection.close()

        except Exception as e:

            print(
                "SIGNAL CLEANUP ERROR:",
                repr(e)
            )

        time.sleep(300)


# =========================================================
# STARTUP
# =========================================================

try:

    init_database()

except Exception as e:

    print(
        "DATABASE STARTUP ERROR:",
        repr(e)
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    try:

        cleanup_thread = threading.Thread(
            target=cleanup_loop,
            daemon=True
        )

        cleanup_thread.start()

    except Exception as e:

        print(
            "CLEANUP THREAD ERROR:",
            repr(e)
        )


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
    
