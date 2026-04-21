from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# =========================
# CONFIG
# =========================

ADMIN_EMAIL = "mjessydk@gmail.com"
HOLD_HOURS = 12

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xExampleEthereumWalletAddress1234567890",
    "USDT": "TExampleUSDTWalletAddress1234567890"
}

# =========================
# DATABASE (PostgreSQL)
# =========================

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# =========================
# INIT DB
# =========================

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id SERIAL PRIMARY KEY,
            name TEXT,
            image TEXT,
            price TEXT,
            holdable BOOLEAN DEFAULT TRUE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS holds (
            id SERIAL PRIMARY KEY,
            user_email TEXT,
            nft_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({"message": "NFT Web3 backend is live"})

# =========================
# GET NFTs
# =========================

@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    try:
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# ADD NFT (ADMIN ONLY)
# =========================

@app.route("/api/nfts", methods=["POST"])
def add_nft():
    data = request.json

    if data.get("email") != ADMIN_EMAIL:
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (name, image, price, holdable)
        VALUES (%s, %s, %s, %s)
        RETURNING *
    """, (
        data.get("name"),
        data.get("image"),
        data.get("price"),
        True
    ))

    new_nft = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return jsonify(new_nft)


# =========================
# HOLD NFT
# =========================

@app.route("/api/hold", methods=["POST"])
def hold_nft():
    data = request.json

    email = data.get("email")
    nft_id = data.get("nft_id")

    if not email or not nft_id:
        return jsonify({"error": "Missing data"}), 400

    start_time = datetime.utcnow()
    end_time = start_time + timedelta(hours=HOLD_HOURS)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO holds (user_email, nft_id, start_time, end_time, status)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING *
    """, (
        email,
        nft_id,
        start_time,
        end_time,
        "active"
    ))

    hold = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "message": "NFT held successfully",
        "hold": hold
    })


# =========================
# REGISTER
# =========================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users (email, password)
            VALUES (%s, %s)
        """, (email, password))

        conn.commit()

        return jsonify({"message": "User registered"})

    except:
        return jsonify({"error": "User already exists"}), 400

    finally:
        cur.close()
        conn.close()


# =========================
# LOGIN
# =========================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM users WHERE email=%s AND password=%s
    """, (email, password))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"error": "Invalid credentials"}), 401


# =========================
# RUN (Railway uses gunicorn)
# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)