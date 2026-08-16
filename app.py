from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

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
    learning_skill = data.get("learningSkill", "").strip()
    bio = data.get("bio", "").strip()

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

    # Correct password hashing line
    hashed_password = generate_password_hash(password)

    cursor = connection.execute(
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
        VALUES (?, ?, ?, ?, ?, ?)
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

    user_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "skill": skill,
            "learningSkill": learning_skill,
            "bio": bio
        }
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

    if not user:
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    if not check_password_hash(
        user["password"],
        password
    ):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    return jsonify({
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "skill": user["skill"] or "",
            "learningSkill": user["learning_skill"] or "",
            "bio": user["bio"] or ""
        }
    })


# ==========================================
# GET USERS
# ==========================================

@app.route("/api/users", methods=["GET"])
def get_users():

    connection = get_connection()

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
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    result = []

    for user in users:
        result.append({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "skill": user["skill"] or "",
            "learningSkill": user["learning_skill"] or "",
            "bio": user["bio"] or ""
        })

    return jsonify({
        "success": True,
        "users": result
    })


# ==========================================
# SEND REQUEST
# ==========================================

@app.route("/api/requests", methods=["POST"])
def create_request():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    sender_id = data.get("senderId")
    receiver_id = data.get("receiverId")
    skill = data.get("skill", "").strip()

    if not sender_id or not receiver_id or not skill:
        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    if int(sender_id) == int(receiver_id):
        return jsonify({
            "success": False,
            "message": "You cannot send a request to yourself."
        }), 400

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM requests
        WHERE
            sender_id = ?
            AND receiver_id = ?
            AND status = 'pending'
        """,
        (
            sender_id,
            receiver_id
        )
    ).fetchone()

    if existing:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Request already sent."
        }), 409

    cursor = connection.execute(
        """
        INSERT INTO requests
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

    request_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Request sent successfully.",
        "requestId": request_id
    }), 201


# ==========================================
# GET RECEIVED REQUESTS
# ==========================================

@app.route("/api/requests/<int:user_id>", methods=["GET"])
def get_requests(user_id):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            r.id AS request_id,
            r.skill AS request_skill,
            r.status AS request_status,
            r.created_at,
            u.id AS sender_id,
            u.name AS sender_name,
            u.email AS sender_email,
            u.skill AS sender_skill
        FROM requests r
        JOIN users u
            ON r.sender_id = u.id
        WHERE r.receiver_id = ?
        ORDER BY r.id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    requests = []

    for row in rows:
        requests.append({
            "id": row["request_id"],
            "skill": row["request_skill"],
            "status": row["request_status"],
            "createdAt": row["created_at"],
            "sender": {
                "id": row["sender_id"],
                "name": row["sender_name"],
                "email": row["sender_email"],
                "skill": row["sender_skill"] or ""
            }
        })

    return jsonify({
        "success": True,
        "requests": requests
    })


# ==========================================
# ACCEPT / REJECT REQUEST
# ==========================================

@app.route("/api/requests/<int:request_id>", methods=["PUT"])
def update_request(request_id):

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    new_status = data.get("status")

    if new_status not in ["accepted", "rejected"]:
        return jsonify({
            "success": False,
            "message": "Invalid request status."
        }), 400

    connection = get_connection()

    existing = connection.execute(
        """
        SELECT id
        FROM requests
        WHERE id = ?
        """,
        (request_id,)
    ).fetchone()

    if not existing:
        connection.close()

        return jsonify({
            "success": False,
            "message": "Request not found."
        }), 404

    connection.execute(
        """
        UPDATE requests
        SET status = ?
        WHERE id = ?
        """,
        (
            new_status,
            request_id
        )
    )

    connection.commit()
    connection.close()

    return jsonify({
        "success": True,
        "message": "Request updated successfully.",
        "status": new_status
    })


# ==========================================
# CONNECTIONS
# ==========================================

@app.route("/api/connections/<int:user_id>", methods=["GET"])
def get_connections(user_id):

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.skill,
            u.learning_skill
        FROM requests r
        JOIN users u
            ON u.id =
                CASE
                    WHEN r.sender_id = ?
                    THEN r.receiver_id
                    ELSE r.sender_id
                END
        WHERE
            (
                r.sender_id = ?
                OR r.receiver_id = ?
            )
            AND r.status = 'accepted'
        ORDER BY r.id DESC
        """,
        (
            user_id,
            user_id,
            user_id
        )
    ).fetchall()

    connection.close()

    connections = []

    for user in rows:

        connections.append({
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "skill": user["skill"] or "",
            "learningSkill": user["learning_skill"] or ""
        })

    return jsonify({
        "success": True,
        "connections": connections
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
