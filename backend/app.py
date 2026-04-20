import os
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

ADMIN_EMAIL = "mjessydk@gmail.com"
HOLD_HOURS = 12

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xExampleEthereumWalletAddress1234567890",
    "USDT": "TExampleUSDTWalletAddress1234567890"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def parse_dt(dt_string):
    if not dt_string:
        return None
    try:
        return datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            image_url TEXT NOT NULL,
            price TEXT NOT NULL,
            creator_email TEXT NOT NULL,
            hold_status TEXT DEFAULT 'available',
            holder_email TEXT,
            hold_until TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nft_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            coin TEXT NOT NULL,
            amount TEXT NOT NULL,
            deposit_wallet TEXT NOT NULL,
            tx_reference TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (nft_id) REFERENCES nfts (id)
        )
    """)

    conn.commit()
    conn.close()


def release_expired_holds():
    conn = get_db_connection()
    cur = conn.cursor()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        UPDATE nfts
        SET hold_status = 'available',
            holder_email = NULL,
            hold_until = NULL
        WHERE hold_status = 'held'
          AND hold_until IS NOT NULL
          AND hold_until <= ?
    """, (now,))

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return {
        "status": "running",
        "message": "NFT Web3 backend is live"
    }, 200


@app.route("/test")
def test():
    return "TEST OK", 200


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({
            "status": "error",
            "message": "All fields are required."
        }), 400

    conn = get_db_connection()
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Email already registered."
        }), 400

    hashed_password = generate_password_hash(password)

    cur.execute("""
        INSERT INTO users (username, email, password, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, email, hashed_password, utc_now_str()))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Registration successful."
    }), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required."
        }), 400

    conn = get_db_connection()
    user = conn.execute("""
        SELECT id, username, email, password
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user["password"], password):
        return jsonify({
            "status": "error",
            "message": "Invalid email or password."
        }), 401

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }), 200


@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    price = (data.get("price") or "").strip()
    creator_email = (data.get("creator_email") or "").strip().lower()

    if not title or not image_url or not price or not creator_email:
        return jsonify({
            "status": "error",
            "message": "All NFT fields are required."
        }), 400

    if creator_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Only the admin can create NFTs."
        }), 403

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (title, image_url, price, creator_email, hold_status, created_at)
        VALUES (?, ?, ?, ?, 'available', ?)
    """, (title, image_url, price, creator_email, utc_now_str()))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created successfully."
    }), 201


@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    release_expired_holds()

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT id, title, image_url, price, creator_email, hold_status, holder_email, hold_until, created_at
        FROM nfts
        ORDER BY id DESC
    """).fetchall()
    conn.close()

    nfts = []
    for row in rows:
        nfts.append({
            "id": row["id"],
            "title": row["title"],
            "image_url": row["image_url"],
            "price": row["price"],
            "creator_email": row["creator_email"],
            "hold_status": row["hold_status"],
            "holder_email": row["holder_email"],
            "hold_until": row["hold_until"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "nfts": nfts,
        "deposit_wallets": DEPOSIT_WALLETS
    }), 200


@app.route("/api/external-nfts", methods=["GET"])
def external_nfts():
    external = [
        {
            "title": "External NFT 1",
            "image_url": "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?q=80&w=1200&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "OpenSea"
        },
        {
            "title": "External NFT 2",
            "image_url": "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=1200&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "OpenSea"
        },
        {
            "title": "External NFT 3",
            "image_url": "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=1200&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "OpenSea"
        },
        {
            "title": "External NFT 4",
            "image_url": "https://images.unsplash.com/photo-1545987796-200677ee1011?q=80&w=1200&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "OpenSea"
        }
    ]

    return jsonify({
        "external_nfts": external
    }), 200


@app.route("/api/create-deposit-request", methods=["POST"])
def create_deposit_request():
    release_expired_holds()

    data = request.get_json(silent=True) or {}

    nft_id = data.get("nft_id")
    user_email = (data.get("user_email") or "").strip().lower()
    coin = (data.get("coin") or "").strip().upper()
    tx_reference = (data.get("tx_reference") or "").strip()

    if not nft_id or not user_email or not coin:
        return jsonify({
            "status": "error",
            "message": "NFT, user email, and coin are required."
        }), 400

    if coin not in DEPOSIT_WALLETS:
        return jsonify({
            "status": "error",
            "message": "Invalid deposit coin."
        }), 400

    conn = get_db_connection()
    cur = conn.cursor()

    nft = cur.execute("""
        SELECT id, title, price, hold_status, holder_email
        FROM nfts
        WHERE id = ?
    """, (nft_id,)).fetchone()

    if not nft:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "NFT not found."
        }), 404

    if nft["hold_status"] == "held":
        conn.close()
        return jsonify({
            "status": "error",
            "message": "This NFT is already held."
        }), 400

    pending = cur.execute("""
        SELECT id
        FROM deposit_requests
        WHERE nft_id = ?
          AND user_email = ?
          AND status = 'pending'
    """, (nft_id, user_email)).fetchone()

    if pending:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "You already have a pending deposit request for this NFT."
        }), 400

    cur.execute("""
        INSERT INTO deposit_requests (
            nft_id, user_email, coin, amount, deposit_wallet, tx_reference, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        nft_id,
        user_email,
        coin,
        nft["price"],
        DEPOSIT_WALLETS[coin],
        tx_reference,
        utc_now_str()
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request submitted successfully."
    }), 201


@app.route("/api/pending-deposits", methods=["GET"])
def pending_deposits():
    admin_email = (request.args.get("user_email") or "").strip().lower()

    if admin_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required."
        }), 403

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT
            dr.id,
            dr.nft_id,
            dr.user_email,
            dr.coin,
            dr.amount,
            dr.deposit_wallet,
            dr.tx_reference,
            dr.status,
            dr.created_at,
            n.title AS nft_title
        FROM deposit_requests dr
        JOIN nfts n ON dr.nft_id = n.id
        WHERE dr.status = 'pending'
        ORDER BY dr.id DESC
    """).fetchall()
    conn.close()

    deposits = []
    for row in rows:
        deposits.append({
            "id": row["id"],
            "nft_id": row["nft_id"],
            "nft_title": row["nft_title"],
            "user_email": row["user_email"],
            "coin": row["coin"],
            "amount": row["amount"],
            "deposit_wallet": row["deposit_wallet"],
            "tx_reference": row["tx_reference"],
            "status": row["status"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "deposits": deposits
    }), 200


@app.route("/api/confirm-deposit", methods=["POST"])
def confirm_deposit():
    release_expired_holds()

    data = request.get_json(silent=True) or {}

    deposit_id = data.get("deposit_id")
    admin_email = (data.get("admin_email") or "").strip().lower()

    if not deposit_id or not admin_email:
        return jsonify({
            "status": "error",
            "message": "Deposit ID and admin email are required."
        }), 400

    if admin_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required."
        }), 403

    conn = get_db_connection()
    cur = conn.cursor()

    deposit = cur.execute("""
        SELECT id, nft_id, user_email, status
        FROM deposit_requests
        WHERE id = ?
    """, (deposit_id,)).fetchone()

    if not deposit:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request not found."
        }), 404

    if deposit["status"] != "pending":
        conn.close()
        return jsonify({
            "status": "error",
            "message": "This deposit request is no longer pending."
        }), 400

    nft = cur.execute("""
        SELECT id, hold_status
        FROM nfts
        WHERE id = ?
    """, (deposit["nft_id"],)).fetchone()

    if not nft:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Related NFT not found."
        }), 404

    if nft["hold_status"] == "held":
        conn.close()
        return jsonify({
            "status": "error",
            "message": "NFT is already held."
        }), 400

    hold_until = (datetime.utcnow() + timedelta(hours=HOLD_HOURS)).strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        UPDATE nfts
        SET hold_status = 'held',
            holder_email = ?,
            hold_until = ?
        WHERE id = ?
    """, (deposit["user_email"], hold_until, deposit["nft_id"]))

    cur.execute("""
        UPDATE deposit_requests
        SET status = 'confirmed'
        WHERE id = ?
    """, (deposit_id,))

    cur.execute("""
        UPDATE deposit_requests
        SET status = 'rejected'
        WHERE nft_id = ?
          AND id != ?
          AND status = 'pending'
    """, (deposit["nft_id"], deposit_id))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit confirmed. Hold is now active for 12 hours."
    }), 200


@app.route("/api/reject-deposit", methods=["POST"])
def reject_deposit():
    data = request.get_json(silent=True) or {}

    deposit_id = data.get("deposit_id")
    admin_email = (data.get("admin_email") or "").strip().lower()

    if not deposit_id or not admin_email:
        return jsonify({
            "status": "error",
            "message": "Deposit ID and admin email are required."
        }), 400

    if admin_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required."
        }), 403

    conn = get_db_connection()
    cur = conn.cursor()

    deposit = cur.execute("""
        SELECT id, status
        FROM deposit_requests
        WHERE id = ?
    """, (deposit_id,)).fetchone()

    if not deposit:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request not found."
        }), 404

    if deposit["status"] != "pending":
        conn.close()
        return jsonify({
            "status": "error",
            "message": "This deposit request is no longer pending."
        }), 400

    cur.execute("""
        UPDATE deposit_requests
        SET status = 'rejected'
        WHERE id = ?
    """, (deposit_id,))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request rejected."
    }), 200


init_db()
release_expired_holds()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)