import os
from datetime import datetime, timedelta

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
HOLD_HOURS = 12

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

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # NFTS
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

    # DEPOSIT REQUESTS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS deposit_requests (
            id SERIAL PRIMARY KEY,
            nft_id INTEGER,
            nft_title TEXT,
            user_email TEXT,
            coin TEXT,
            amount TEXT,
            deposit_wallet TEXT,
            tx_reference TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

# =========================
# HELPERS
# =========================
def is_admin(email):
    return (email or "").strip().lower() == ADMIN_EMAIL.lower()

def serialize_timestamp(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return jsonify({
        "message": "NFT Web3 backend is live",
        "status": "running"
    })

# =========================
# AUTH
# =========================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields required"}), 400

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
        conn.rollback()
        return jsonify({
            "status": "error",
            "message": "User already exists"
        }), 400

    finally:
        cur.close()
        conn.close()

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password required"
        }), 400

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

    return jsonify({
        "status": "error",
        "message": "Invalid credentials"
    }), 401

# =========================
# NFT ROUTES
# =========================
@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM nfts ORDER BY id DESC")
    nfts = cur.fetchall()

    # convert timestamps safely
    cleaned = []
    for nft in nfts:
        item = dict(nft)
        item["hold_until"] = serialize_timestamp(item.get("hold_until"))
        item["created_at"] = serialize_timestamp(item.get("created_at"))
        cleaned.append(item)

    cur.close()
    conn.close()

    return jsonify({
        "deposit_wallets": DEPOSIT_WALLETS,
        "nfts": cleaned
    })

@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.json or {}

    title = data.get("title")
    image_url = data.get("image_url")
    price = data.get("price")
    creator_email = data.get("creator_email")

    if not title or not image_url or not price or not creator_email:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    if not is_admin(creator_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

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

    nft = dict(nft)
    nft["hold_until"] = serialize_timestamp(nft.get("hold_until"))
    nft["created_at"] = serialize_timestamp(nft.get("created_at"))

    return jsonify({
        "status": "success",
        "message": "NFT created",
        "nft": nft
    })

# =========================
# EXTERNAL NFTS
# =========================
@app.route("/api/external-nfts", methods=["GET"])
def external_nfts():
    fallback = [
        {
            "title": "Featured NFT 1",
            "image_url": "https://images.unsplash.com/photo-1545239351-1141bd82e8a6?q=80&w=900&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "featured"
        },
        {
            "title": "Featured NFT 2",
            "image_url": "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4?q=80&w=900&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "featured"
        },
        {
            "title": "Featured NFT 3",
            "image_url": "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?q=80&w=900&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "featured"
        },
        {
            "title": "Featured NFT 4",
            "image_url": "https://images.unsplash.com/photo-1642104704074-907c0698cbd9?q=80&w=900&auto=format&fit=crop",
            "link": "https://opensea.io/",
            "source": "featured"
        }
    ]

    return jsonify({
        "status": "success",
        "external_nfts": fallback
    })

# =========================
# HOLD / DEPOSIT ROUTES
# =========================
@app.route("/api/create-deposit-request", methods=["POST"])
def create_deposit_request():
    data = request.json or {}

    nft_id = data.get("nft_id")
    user_email = data.get("user_email")
    coin = data.get("coin")
    tx_reference = data.get("tx_reference", "").strip()

    if not nft_id or not user_email or not coin:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    coin = coin.upper()
    if coin not in DEPOSIT_WALLETS:
        return jsonify({
            "status": "error",
            "message": "Unsupported coin selected"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM nfts WHERE id = %s", (nft_id,))
    nft = cur.fetchone()

    if not nft:
      cur.close()
      conn.close()
      return jsonify({
          "status": "error",
          "message": "NFT not found"
      }), 404

    if nft["hold_status"] == "held":
        cur.close()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "This NFT is already held"
        }), 400

    cur.execute("""
        INSERT INTO deposit_requests (
            nft_id, nft_title, user_email, coin, amount, deposit_wallet, tx_reference
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
    """, (
        nft_id,
        nft["title"],
        user_email,
        coin,
        nft["price"],
        DEPOSIT_WALLETS[coin],
        tx_reference
    ))

    deposit = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    deposit = dict(deposit)
    deposit["created_at"] = serialize_timestamp(deposit.get("created_at"))

    return jsonify({
        "status": "success",
        "message": "Deposit request submitted successfully",
        "deposit": deposit
    })

@app.route("/api/pending-deposits", methods=["GET"])
def pending_deposits():
    user_email = request.args.get("user_email")

    if not is_admin(user_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM deposit_requests
        WHERE status = 'pending'
        ORDER BY id DESC
    """)
    deposits = cur.fetchall()

    cleaned = []
    for deposit in deposits:
        item = dict(deposit)
        item["created_at"] = serialize_timestamp(item.get("created_at"))
        cleaned.append(item)

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "deposits": cleaned
    })

@app.route("/api/confirm-deposit", methods=["POST"])
def confirm_deposit():
    data = request.json or {}

    deposit_id = data.get("deposit_id")
    admin_email = data.get("admin_email")

    if not deposit_id or not is_admin(admin_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM deposit_requests
        WHERE id = %s
    """, (deposit_id,))
    deposit = cur.fetchone()

    if not deposit:
        cur.close()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request not found"
        }), 404

    if deposit["status"] != "pending":
        cur.close()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request already processed"
        }), 400

    hold_until = datetime.utcnow() + timedelta(hours=HOLD_HOURS)

    cur.execute("""
        UPDATE deposit_requests
        SET status = 'confirmed'
        WHERE id = %s
    """, (deposit_id,))

    cur.execute("""
        UPDATE nfts
        SET hold_status = 'held',
            holder_email = %s,
            hold_until = %s
        WHERE id = %s
    """, (
        deposit["user_email"],
        hold_until,
        deposit["nft_id"]
    ))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit confirmed and NFT is now held"
    })

@app.route("/api/reject-deposit", methods=["POST"])
def reject_deposit():
    data = request.json or {}

    deposit_id = data.get("deposit_id")
    admin_email = data.get("admin_email")

    if not deposit_id or not is_admin(admin_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM deposit_requests
        WHERE id = %s
    """, (deposit_id,))
    deposit = cur.fetchone()

    if not deposit:
        cur.close()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request not found"
        }), 404

    if deposit["status"] != "pending":
        cur.close()
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request already processed"
        }), 400

    cur.execute("""
        UPDATE deposit_requests
        SET status = 'rejected'
        WHERE id = %s
    """, (deposit_id,))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request rejected"
    })

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)