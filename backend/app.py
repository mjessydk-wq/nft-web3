from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
CORS(app)

DATABASE = "database.db"

ADMIN_EMAIL = "mjessydk@gmail.com"

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xExampleEthereumWalletAddress1234567890",
    "USDT": "TExampleUSDTWalletAddress1234567890"
}


# -------------------------
# DATABASE HELPERS
# -------------------------
def get_conn():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL,
            hold_hours INTEGER DEFAULT 12,
            profit_percent REAL DEFAULT 10,
            is_holdable INTEGER DEFAULT 1,
            creator_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (creator_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS holds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            nft_id INTEGER NOT NULL,
            coin TEXT NOT NULL,
            tx_ref TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (nft_id) REFERENCES nfts(id)
        )
    """)

    conn.commit()
    conn.close()


def seed_admin_user():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (ADMIN_EMAIL,))
    admin = cur.fetchone()

    if not admin:
        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "admin",
            ADMIN_EMAIL,
            generate_password_hash("admin123"),
            1,
            datetime.utcnow().isoformat()
        ))
        conn.commit()

    conn.close()


def row_to_user(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "is_admin": bool(row["is_admin"])
    }


def row_to_nft(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "image": row["image"],
        "description": row["description"],
        "price": row["price"],
        "hold_hours": row["hold_hours"],
        "profit_percent": row["profit_percent"],
        "is_holdable": bool(row["is_holdable"]),
        "creator_id": row["creator_id"],
        "created_at": row["created_at"]
    }


init_db()
seed_admin_user()


# -------------------------
# BASIC ROUTES
# -------------------------
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "NFT Web3 backend is live",
        "status": "running"
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "database": "connected"
    })


@app.route("/api/wallets", methods=["GET"])
def wallets():
    return jsonify({
        "deposit_wallets": DEPOSIT_WALLETS
    })


# -------------------------
# AUTH ROUTES
# -------------------------
@app.route("/api/register", methods=["POST"])
def register():
    try:
        data = request.get_json()

        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not username or not email or not password:
            return jsonify({"error": "Username, email, and password are required."}), 400

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = ?", (email,))
        existing = cur.fetchone()

        if existing:
            conn.close()
            return jsonify({"error": "Email already exists."}), 400

        is_admin = 1 if email == ADMIN_EMAIL.lower() else 0

        cur.execute("""
            INSERT INTO users (username, email, password_hash, is_admin, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            username,
            email,
            generate_password_hash(password),
            is_admin,
            datetime.utcnow().isoformat()
        ))

        conn.commit()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        return jsonify({
            "message": "Registration successful.",
            "user": row_to_user(user)
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def login():
    try:
        data = request.get_json()

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "Invalid email or password."}), 401

        if not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        return jsonify({
            "message": "Login successful.",
            "user": row_to_user(user)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# NFT ROUTES
# -------------------------
@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM nfts
            ORDER BY id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        nfts = [row_to_nft(row) for row in rows]
        return jsonify(nfts)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/nfts", methods=["POST"])
def create_nft():
    try:
        data = request.get_json()

        user_id = data.get("user_id")
        name = (data.get("name") or "").strip()
        image = (data.get("image") or "").strip()
        description = (data.get("description") or "").strip()
        price = data.get("price")
        hold_hours = data.get("hold_hours", 12)
        profit_percent = data.get("profit_percent", 10)
        is_holdable = 1 if data.get("is_holdable", 1) else 0

        if not user_id:
            return jsonify({"error": "Missing user_id."}), 400

        if not name or not image or price is None:
            return jsonify({"error": "Name, image, and price are required."}), 400

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            conn.close()
            return jsonify({"error": "User not found."}), 404

        if not user["is_admin"]:
            conn.close()
            return jsonify({"error": "Admin access required."}), 403

        cur.execute("""
            INSERT INTO nfts (
                name, image, description, price, hold_hours, profit_percent,
                is_holdable, creator_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            image,
            description,
            float(price),
            int(hold_hours),
            float(profit_percent),
            is_holdable,
            user_id,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return jsonify({"message": "NFT created successfully."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# HOLD ROUTES
# -------------------------
@app.route("/api/hold", methods=["POST"])
def hold_nft():
    try:
        data = request.get_json()

        user_id = data.get("user_id")
        nft_id = data.get("nft_id")
        coin = (data.get("coin") or "").strip().upper()
        tx_ref = (data.get("tx_ref") or "").strip()

        if not user_id or not nft_id or not coin:
            return jsonify({"error": "user_id, nft_id, and coin are required."}), 400

        if coin not in DEPOSIT_WALLETS:
            return jsonify({"error": "Invalid coin selected."}), 400

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            conn.close()
            return jsonify({"error": "User not found."}), 404

        if user["is_admin"]:
            conn.close()
            return jsonify({"error": "Admin cannot hold NFTs."}), 403

        cur.execute("SELECT * FROM nfts WHERE id = ?", (nft_id,))
        nft = cur.fetchone()

        if not nft:
            conn.close()
            return jsonify({"error": "NFT not found."}), 404

        if not nft["is_holdable"]:
            conn.close()
            return jsonify({"error": "This NFT is not holdable."}), 400

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=int(nft["hold_hours"]))

        cur.execute("""
            INSERT INTO holds (
                user_id, nft_id, coin, tx_ref, status, start_time, end_time, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            nft_id,
            coin,
            tx_ref,
            "pending",
            start_time.isoformat(),
            end_time.isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "NFT hold placed successfully.",
            "wallet_address": DEPOSIT_WALLETS[coin],
            "coin": coin,
            "status": "pending",
            "end_time": end_time.isoformat()
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/my-holds", methods=["GET"])
def my_holds():
    try:
        user_id = request.args.get("user_id", type=int)

        if not user_id:
            return jsonify({"error": "user_id is required."}), 400

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                holds.id,
                holds.coin,
                holds.tx_ref,
                holds.status,
                holds.start_time,
                holds.end_time,
                nfts.name AS nft_name,
                nfts.price,
                nfts.profit_percent
            FROM holds
            JOIN nfts ON holds.nft_id = nfts.id
            WHERE holds.user_id = ?
            ORDER BY holds.id DESC
        """, (user_id,))

        rows = cur.fetchall()
        conn.close()

        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "coin": row["coin"],
                "tx_ref": row["tx_ref"],
                "status": row["status"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "nft_name": row["nft_name"],
                "price": row["price"],
                "profit_percent": row["profit_percent"]
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# OPTIONAL DEBUG ROUTE
# -------------------------
@app.route("/api/debug/reset-nfts", methods=["POST"])
def reset_nfts():
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM holds")
        cur.execute("DELETE FROM nfts")

        conn.commit()
        conn.close()

        return jsonify({"message": "NFTs and holds cleared."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)