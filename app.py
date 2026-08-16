from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

users = []


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "Talent Exchange Python Backend is running!"
    })


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

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "message": "Password must contain at least 6 characters."
        }), 400

    for user in users:
        if user["email"] == email:
            return jsonify({
                "success": False,
                "message": "An account with this email already exists."
            }), 409

    hashed_password = generate_password_hash(password)

    user = {
        "name": name,
        "email": email,
        "password": hashed_password,
        "skill": "",
        "learningSkill": "",
        "bio": ""
    }

    users.append(user)

    return jsonify({
        "success": True,
        "message": "Account created successfully."
    }), 201


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

    for user in users:

        if user["email"] == email:

            if check_password_hash(
                user["password"],
                password
            ):

                return jsonify({
                    "success": True,
                    "message": "Login successful.",
                    "user": {
                        "name": user["name"],
                        "email": user["email"],
                        "skill": user["skill"],
                        "learningSkill": user["learningSkill"],
                        "bio": user["bio"]
                    }
                })

            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

    return jsonify({
        "success": False,
        "message": "Invalid email or password."
    }), 401


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
