from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
ADMIN_EMAIL = "mjessydk@gmail.com"
HOLD_HOURS = 12

# =========================
# DATABASE
# =========================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nfts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        price REAL,
        image TEXT,
        is_admin INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nft_id INTEGER,
        user_email TEXT,
        expires_at TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# HOME ROUTE (VERY IMPORTANT)
# =========================
@app.route("/")
def home():
    return jsonify({"message": "NFT Web3 Backend is Running 🚀"})

# =========================
# AUTH
# =========================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    hashed = generate_password_hash(password)

    try:
        conn = get_db()
        conn.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed))
        conn.commit()
        return jsonify({"message": "User registered"})
    except:
        return jsonify({"error": "User already exists"}), 400

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if user and check_password_hash(user["password"], password):
        return jsonify({"message": "Login successful", "email": email})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# =========================
# NFT ROUTES
# =========================
@app.route("/api/nfts")
def get_nfts():
    conn = get_db()
    nfts = conn.execute("SELECT * FROM nfts ORDER BY is_admin DESC").fetchall()

    return jsonify([dict(nft) for nft in nfts])

@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.json

    if data.get("admin_email") != ADMIN_EMAIL:
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db()
    conn.execute("""
        INSERT INTO nfts (title, price, image, is_admin)
        VALUES (?, ?, ?, 1)
    """, (data["title"], data["price"], data["image"]))

    conn.commit()
    return jsonify({"message": "NFT created"})

# =========================
# HOLD SYSTEM
# =========================
def expire_holds():
    conn = get_db()
    now = datetime.utcnow()

    holds = conn.execute("SELECT * FROM holds").fetchall()

    for hold in holds:
        if datetime.fromisoformat(hold["expires_at"]) < now:
            conn.execute("DELETE FROM holds WHERE id = ?", (hold["id"],))

    conn.commit()

@app.route("/api/hold", methods=["POST"])
def hold_nft():
    data = request.json

    nft_id = data["nft_id"]
    email = data["email"]

    expires = datetime.utcnow() + timedelta(hours=HOLD_HOURS)

    conn = get_db()
    conn.execute("""
        INSERT INTO holds (nft_id, user_email, expires_at)
        VALUES (?, ?, ?)
    """, (nft_id, email, expires.isoformat()))

    conn.commit()

    return jsonify({
        "message": "NFT held successfully",
        "expires_at": expires.isoformat()
    })

# =========================
# RUN APP (RAILWAY FIX)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)