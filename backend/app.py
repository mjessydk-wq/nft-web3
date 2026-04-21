import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================
ADMIN_EMAIL = "mjessydk@gmail.com"

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xExampleEthereumWalletAddress1234567890",
    "USDT": "TExampleUSDTWalletAddress1234567890"
}

DATABASE_URL = os.getenv("DATABASE_URL")

# =========================
# DATABASE CONNECTION
# =========================
def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = get_db()
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # NFT TABLE
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id SERIAL PRIMARY KEY,
            title TEXT,
            image_url TEXT,
            price TEXT,
            creator_email TEXT,
            hold_status TEXT DEFAULT 'available',
            holder_email TEXT,
            hold_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# =========================
# ROUTES
# =========================

# HEALTH CHECK
@app.route("/")
def home():
    return jsonify({
        "message": "NFT Web3 backend is live",
        "status": "running"
    })

# =========================
# AUTH
# =========================

# REGISTER
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields required"})

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
            RETURNING id, username, email;
        """, (username, email, password))

        user = cur.fetchone()
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Account created",
            "user": user
        })

    except Exception:
        return jsonify({
            "status": "error",
            "message": "User already exists"
        })

    finally:
        cur.close()
        conn.close()

# LOGIN
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, email FROM users
        WHERE email = %s AND password = %s
    """, (email, password))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": user
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        })

# =========================
# NFT ROUTES
# =========================

# GET NFTs
@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM nfts ORDER BY id DESC")
    nfts = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "deposit_wallets": DEPOSIT_WALLETS,
        "nfts": nfts
    })

# CREATE NFT (ADMIN)
@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.json

    title = data.get("title")
    image_url = data.get("image_url")
    price = data.get("price")
    creator_email = data.get("creator_email")

    if creator_email != ADMIN_EMAIL:
        return jsonify({"status": "error", "message": "Not authorized"})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (title, image_url, price, creator_email)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """, (title, image_url, price, creator_email))

    nft = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created",
        "nft": nft
    })

# =========================
# RUN (LOCAL ONLY)
# =========================
if __name__ == "__main__":
    app.run(debug=True)