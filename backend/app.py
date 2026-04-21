from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import RealDictCursor

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

DATABASE_URL = os.getenv("DATABASE_URL")


# =========================
# DATABASE (PostgreSQL)
# =========================

def get_db():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is missing. Add PostgreSQL variables in Railway.")

    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
        sslmode="require"
    )


# =========================
# INIT DB
# =========================

def init_db():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                image TEXT,
                price TEXT,
                holdable BOOLEAN DEFAULT TRUE
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS holds (
                id SERIAL PRIMARY KEY,
                user_email TEXT NOT NULL,
                nft_id INTEGER NOT NULL REFERENCES nfts(id) ON DELETE CASCADE,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT NOT NULL
            );
        """)

        conn.commit()

    except Exception as e:
        print("DB INIT ERROR:", str(e))
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


try:
    init_db()
except Exception as e:
    print("App startup database error:", str(e))


# =========================
# HELPERS
# =========================

def json_error(message, status=400):
    return jsonify({"error": message}), status


# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({
        "message": "NFT Web3 backend is live",
        "database": "PostgreSQL"
    })


@app.route("/debug-db")
def debug_db():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT NOW() AS server_time;")
        result = cur.fetchone()

        return jsonify({
            "status": "connected",
            "server_time": str(result["server_time"])
        })

    except Exception as e:
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# GET NFTs
# =========================

@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, name, image, price, holdable
            FROM nfts
            ORDER BY id DESC
        """)
        nfts = cur.fetchall()

        return jsonify({
            "deposit_wallets": DEPOSIT_WALLETS,
            "nfts": nfts
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# ADD NFT (ADMIN ONLY)
# =========================

@app.route("/api/nfts", methods=["POST"])
def add_nft():
    data = request.get_json(silent=True) or {}

    if data.get("email") != ADMIN_EMAIL:
        return json_error("Unauthorized", 403)

    name = data.get("name")
    image = data.get("image")
    price = data.get("price")

    if not name:
        return json_error("NFT name is required")
    if not image:
        return json_error("NFT image is required")
    if not price:
        return json_error("NFT price is required")

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO nfts (name, image, price, holdable)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, image, price, holdable
        """, (
            name,
            image,
            price,
            True
        ))

        new_nft = cur.fetchone()
        conn.commit()

        return jsonify(new_nft), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# HOLD NFT
# =========================

@app.route("/api/hold", methods=["POST"])
def hold_nft():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    nft_id = data.get("nft_id")

    if not email or not nft_id:
        return json_error("Missing email or nft_id")

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id, holdable FROM nfts WHERE id = %s", (nft_id,))
        nft = cur.fetchone()

        if not nft:
            return json_error("NFT not found", 404)

        if not nft["holdable"]:
            return json_error("This NFT is not holdable", 400)

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=HOLD_HOURS)

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

        return jsonify({
            "message": "NFT held successfully",
            "hold": hold
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# REGISTER
# =========================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return json_error("Email and password are required")

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO users (email, password)
            VALUES (%s, %s)
            RETURNING id, email
        """, (email, password))

        user = cur.fetchone()
        conn.commit()

        return jsonify({
            "message": "User registered",
            "user": user
        }), 201

    except psycopg2.Error:
        if conn:
            conn.rollback()
        return json_error("User already exists", 400)

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# LOGIN
# =========================

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return json_error("Email and password are required")

    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, email
            FROM users
            WHERE email = %s AND password = %s
        """, (email, password))

        user = cur.fetchone()

        if user:
            return jsonify({
                "message": "Login successful",
                "user": user,
                "is_admin": email == ADMIN_EMAIL
            })

        return json_error("Invalid credentials", 401)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# GET USER HOLDS
# =========================

@app.route("/api/holds/<email>", methods=["GET"])
def get_user_holds(email):
    conn = None
    cur = None

    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT h.id, h.user_email, h.nft_id, h.start_time, h.end_time, h.status,
                   n.name AS nft_name, n.image AS nft_image, n.price AS nft_price
            FROM holds h
            JOIN nfts n ON h.nft_id = n.id
            WHERE h.user_email = %s
            ORDER BY h.id DESC
        """, (email,))

        holds = cur.fetchall()

        return jsonify({"holds": holds})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================
# RUN (Railway uses gunicorn)
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)