from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_connection, init_database


app = Flask(__name__)

CORS(app)


# Initialize database
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


    # Check fields

    if not name or not email or not password:

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


    # Check existing user

    connection = get_connection()

    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()


    if existing_user:

        connection.close()

        return jsonify({
            "success": False,
            "message": "An account with this email already exists."
        }), 409


    # Hash password

    hashed_password = generate_password_hash(password)


    # Insert user

    connection.execute(
        """
        INSERT INTO users
        (name, email, password)
        VALUES (?, ?, ?)
        """,
        (
            name,
            email,
            hashed_password
        )
    )


    connection.commit()

    connection.close()


    return jsonify({
        "success": True,
        "message": "Account created successfully."
    }), 201


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


    email = data.get("email", "").strip().lower()

    password = data.get("password", "")


    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400


    connection = get_connection()


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


    connection.close()


    # User not found

    if not user:

        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401


    # Check password

    if not check_password_hash(
        user["password"],
        password
    ):

        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401


    # Successful login

    return jsonify({

        "success": True,

        "message": "Login successful.",

        "user": {

            "id": user["id"],

            "name": user["name"],

            "email": user["email"],

            "skill": user["skill"] or "",

            "learningSkill":
                user["learning_skill"] or "",

            "bio": user["bio"] or ""

        }

    })


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
