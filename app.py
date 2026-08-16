from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

from database import get_connection, init_database


app = Flask(__name__)

CORS(app)


# ==========================================
# INITIALIZE DATABASE
# ==========================================

init_database()


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    return jsonify({
        "success": True,
        "message": "Talent Exchange Python Backend is running!"
    })


# ==========================================
# SIGNUP
# ==========================================

@app.route("/api/signup", methods=["POST"])
def signup():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400


    name = data.get("name", "").strip()

    email = data.get("email", "").strip().lower()

    password = data.get("password", "")

    skill = data.get("skill", "").strip()


    # Check fields

    if not name or not email or not password or not skill:

        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400


    # Password length

    if len(password) < 6:

        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters."
        }), 400


    connection = get_connection()


    try:

        # Check existing user

        existing_user = connection.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


        if existing_user:

            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409


        # Hash password

        hashed_password =
            generate_password_hash(password)


        # Insert user

        connection.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                skill
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                name,
                email,
                hashed_password,
                skill
            )
        )


        connection.commit()


        return jsonify({

            "success": True,

            "message":
                "Account created successfully."

        }), 201


    finally:

        connection.close()


# ==========================================
# LOGIN
# ==========================================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.get_json()

    if not data:

        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400


    email = data.get(
        "email",
        ""
    ).strip().lower()


    password = data.get(
        "password",
        ""
    )


    if not email or not password:

        return jsonify({
            "success": False,
            "message":
                "Email and password are required."
        }), 400


    connection = get_connection()


    try:

        user = connection.execute(
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

            WHERE email = ?
            """,
            (email,)
        ).fetchone()

    finally:

        connection.close()


    # User not found

    if not user:

        return jsonify({
            "success": False,
            "message":
                "Invalid email or password."
        }), 401


    # Password check

    if not check_password_hash(
        user["password"],
        password
    ):

        return jsonify({
            "success": False,
            "message":
                "Invalid email or password."
        }), 401


    # Successful login

    return jsonify({

        "success": True,

        "message":
            "Login successful.",

        "user": {

            "id":
                user["id"],

            "name":
                user["name"],

            "email":
                user["email"],

            "skill":
                user["skill"] or "",

            "learningSkill":
                user["learning_skill"] or "",

            "bio":
                user["bio"] or ""

        }

    })


# ==========================================
# GET ALL USERS
# ==========================================

@app.route("/api/users", methods=["GET"])
def get_users():

    connection = get_connection()


    try:

        users = connection.execute(
            """
            SELECT
                id,
                name,
                email,
                skill,
                learning_skill,
                bio

            FROM users

            ORDER BY name ASC
            """
        ).fetchall()


        user_list = []


        for user in users:

            user_list.append({

                "id":
                    user["id"],

                "name":
                    user["name"],

                "email":
                    user["email"],

                "skill":
                    user["skill"] or "",

                "learningSkill":
                    user["learning_skill"] or "",

                "bio":
                    user["bio"] or ""

            })


        return jsonify({

            "success": True,

            "users":
                user_list

        })


    finally:

        connection.close()


# ==========================================
# SEND EXCHANGE REQUEST
# ==========================================

@app.route("/api/requests", methods=["POST"])
def create_request():

    data = request.get_json()


    if not data:

        return jsonify({
            "success": False,
            "message":
                "No data received."
        }), 400


    sender_id =
        data.get("senderId")


    receiver_id =
        data.get("receiverId")


    skill =
        data.get("skill", "").strip()


    if not sender_id or not receiver_id or not skill:

        return jsonify({

            "success": False,

            "message":
                "Sender, receiver and skill are required."

        }), 400


    if sender_id == receiver_id:

        return jsonify({

            "success": False,

            "message":
                "You cannot send a request to yourself."

        }), 400


    connection = get_connection()


    try:

        # Check users exist

        sender = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (sender_id,)
        ).fetchone()


        receiver = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = ?
            """,
            (receiver_id,)
        ).fetchone()


        if not sender or not receiver:

            return jsonify({

                "success": False,

                "message":
                    "User not found."

            }), 404


        # Check duplicate pending request

        existing_request = connection.execute(
            """
            SELECT id

            FROM exchange_requests

            WHERE sender_id = ?

            AND receiver_id = ?

            AND skill = ?

            AND status = 'pending'
            """,
            (
                sender_id,
                receiver_id,
                skill
            )
        ).fetchone()


        if existing_request:

            return jsonify({

                "success": False,

                "message":
                    "Request already sent."

            }), 409


        # Create request

        connection.execute(
            """
            INSERT INTO exchange_requests
            (
                sender_id,
                receiver_id,
                skill,
                status
            )

            VALUES (?, ?, ?, 'pending')
            """,
            (
                sender_id,
                receiver_id,
                skill
            )
        )


        connection.commit()


        return jsonify({

            "success": True,

            "message":
                "Exchange request sent successfully."

        }), 201


    finally:

        connection.close()


# ==========================================
# GET RECEIVED REQUESTS
# ==========================================

@app.route("/api/requests/<int:user_id>", methods=["GET"])
def get_requests(user_id):

    connection = get_connection()


    try:

        requests = connection.execute(
            """
            SELECT

                exchange_requests.id,

                exchange_requests.skill,

                exchange_requests.status,

                exchange_requests.created_at,

                users.id AS sender_id,

                users.name AS sender_name,

                users.email AS sender_email,

                users.skill AS sender_skill

            FROM exchange_requests

            JOIN users

                ON exchange_requests.sender_id =
                   users.id

            WHERE exchange_requests.receiver_id = ?

            ORDER BY exchange_requests.created_at DESC
            """,
            (user_id,)
        ).fetchall()


        request_list = []


        for item in requests:

            request_list.append({

                "id":
                    item["id"],

                "skill":
                    item["skill"],

                "status":
                    item["status"],

                "createdAt":
                    item["created_at"],

                "sender": {

                    "id":
                        item["sender_id"],

                    "name":
                        item["sender_name"],

                    "email":
                        item["sender_email"],

                    "skill":
                        item["sender_skill"] or ""

                }

            })


        return jsonify({

            "success": True,

            "requests":
                request_list

        })


    finally:

        connection.close()


# ==========================================
# UPDATE REQUEST STATUS
# ==========================================

@app.route(
    "/api/requests/<int:request_id>",
    methods=["PUT"]
)
def update_request(request_id):

    data = request.get_json()


    if not data:

        return jsonify({

            "success": False,

            "message":
                "No data received."

        }), 400


    status =
        data.get("status", "").strip().lower()


    allowed_statuses = [
        "accepted",
        "rejected"
    ]


    if status not in allowed_statuses:

        return jsonify({

            "success": False,

            "message":
                "Invalid request status."

        }), 400


    connection = get_connection()


    try:

        existing_request = connection.execute(
            """
            SELECT id
            FROM exchange_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()


        if not existing_request:

            return jsonify({

                "success": False,

                "message":
                    "Request not found."

            }), 404


        connection.execute(
            """
            UPDATE exchange_requests

            SET status = ?

            WHERE id = ?
            """,
            (
                status,
                request_id
            )
        )


        connection.commit()


        return jsonify({

            "success": True,

            "message":
                "Request updated successfully."

        })


    finally:

        connection.close()


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
