from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from db import users
from pymongo.errors import PyMongoError

# Blueprint for authentication routes
bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Utility: Strip private fields when returning a user
def _public_user(u):
    """
    Convert a MongoDB user document into a safe public dictionary
    - Excludes password hash
    - Converts _id (ObjectId) into string
    """
    return {"id": str(u["_id"]), "name": u.get("name", ""), "email": u["email"]}


@bp.post("/signup")
def signup():
    """
    Create a new user account.
    Expects JSON {name, email, password}.
    Returns public user dict if successful.
    """
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        # Validation
        if not name or not email or not password:
            return jsonify({"error": "name, email, password are required"}), 400

        # Ensure uniqueness
        if users.find_one({"email": email}):
            return jsonify({"error": "Email already in use"}), 409

        # Hash password before storing
        doc = {
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
        }

        res = users.insert_one(doc)
        u = users.find_one({"_id": res.inserted_id})

        # Start a session
        session.clear()
        session["user_id"] = str(u["_id"])
        session["email"] = u["email"]
        session.permanent = True  # make cookie persistent

        return jsonify({"user": _public_user(u)}), 201

    except PyMongoError as e:
        # Database errors
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        # Catch-all fallback
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@bp.post("/login")
def login():
    """
    Authenticate user by email + password.
    Expects JSON {email, password}.
    Returns public user dict if valid.
    """
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        # Find user by email
        u = users.find_one({"email": email})
        if not u or not check_password_hash(u.get("password", ""), password):
            return jsonify({"error": "Invalid email or password"}), 401

        # Start session
        session.clear()
        session["user_id"] = str(u["_id"])
        session["email"] = u["email"]
        session.permanent = True

        return jsonify({"user": _public_user(u)})

    except PyMongoError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@bp.post("/logout")
def logout():
    """
    Clear the session cookie → logs user out.
    """
    try:
        session.clear()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@bp.get("/me")
def me():
    """
    Get the currently logged-in user's public profile.
    Uses session cookie.
    """
    try:
        if "user_id" not in session:
            return jsonify({"user": None}), 200

        u = users.find_one({"email": session.get("email")})
        return jsonify({"user": _public_user(u) if u else None}), 200
    except PyMongoError as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
