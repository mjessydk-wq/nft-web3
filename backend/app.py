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
# DATABASE
# =========================
def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def serialize_dt(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

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

def nft_to_json(row):
    item = dict(row)
    item["hold_until"] = serialize_dt(item.get("hold_until"))
    item["created_at"] = serialize_dt(item.get("created_at"))
    return item

# =========================
# BASIC
# =========================
@app.route("/", methods=["GET"])
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

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({
            "status": "error",
            "message": "All fields required"
        }), 400

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

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password required"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, username, email
        FROM users
        WHERE email = %s AND password = %s
    """, (email, password))

    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Invalid credentials"
        }), 401

    return jsonify({
        "status": "success",
        "message": "Login successful",
        "user": user
    })

# =========================
# NFT ROUTES
# =========================
@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM nfts ORDER BY id DESC")
    nfts = [nft_to_json(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify({
        "deposit_wallets": DEPOSIT_WALLETS,
        "nfts": nfts
    })

# Works with your current create-nft.html frontend payload:
# { title, image_url, price, creator_email }
@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.json or {}

    title = (data.get("title") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    price = (data.get("price") or "").strip()
    creator_email = (data.get("creator_email") or "").strip().lower()

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

    nft = nft_to_json(cur.fetchone())
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created",
        "nft": nft
    })

# Also supports direct POST /api/nfts with:
# { name, image, price, holdable }
@app.route("/api/nfts", methods=["POST"])
def add_nft():
    data = request.json or {}

    title = (data.get("name") or data.get("title") or "").strip()
    image_url = (data.get("image") or data.get("image_url") or "").strip()
    price = (data.get("price") or "").strip()

    if not title or not image_url or not price:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (title, image_url, price, creator_email)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """, (title, image_url, price, ADMIN_EMAIL))

    nft = nft_to_json(cur.fetchone())
    conn.commit()

    cur.close()
    conn.close()

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
# HOLD / DEPOSITS
# =========================
@app.route("/api/create-deposit-request", methods=["POST"])
def create_deposit_request():
    data = request.json or {}

    nft_id = data.get("nft_id")
    user_email = (data.get("user_email") or "").strip().lower()
    coin = (data.get("coin") or "").strip().upper()
    tx_reference = (data.get("tx_reference") or "").strip()

    if not nft_id or not user_email or not coin:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

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

    deposit = dict(cur.fetchone())
    deposit["created_at"] = serialize_dt(deposit.get("created_at"))
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request submitted successfully",
        "deposit": deposit
    })

@app.route("/api/pending-deposits", methods=["GET"])
def pending_deposits():
    user_email = request.args.get("user_email", "")

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
    deposits = []
    for row in cur.fetchall():
        item = dict(row)
        item["created_at"] = serialize_dt(item.get("created_at"))
        deposits.append(item)

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "deposits": deposits
    })

@app.route("/api/confirm-deposit", methods=["POST"])
def confirm_deposit():
    data = request.json or {}

    deposit_id = data.get("deposit_id")
    admin_email = (data.get("admin_email") or "").strip().lower()

    if not deposit_id or not is_admin(admin_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deposit_requests WHERE id = %s", (deposit_id,))
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
    admin_email = (data.get("admin_email") or "").strip().lower()

    if not deposit_id or not is_admin(admin_email):
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM deposit_requests WHERE id = %s", (deposit_id,))
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
# SEED SAMPLE NFTS
# =========================
@app.route("/api/seed-nfts", methods=["GET"])
def seed_nfts():
    conn = get_db()
    cur = conn.cursor()

    sample_nfts = [
        ("Neon Panther Genesis", "https://images.unsplash.com/photo-1614850523459-c2f4c699c52c", "0.42"),
        ("Cyber Mask #12", "https://images.unsplash.com/photo-1642104704074-907c0698cbd9", "0.65"),
        ("Galaxy Ape Prime", "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4", "0.88"),
        ("Royal Skull Vault", "https://images.unsplash.com/photo-1545239351-1141bd82e8a6", "1.10"),
        ("Meta Samurai", "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4", "0.73"),
        ("Glitch Lion X", "https://images.unsplash.com/photo-1516321318423-f06f85e504b3", "1.25")
    ]

    for title, image_url, price in sample_nfts:
        cur.execute("""
            INSERT INTO nfts (title, image_url, price, creator_email)
            VALUES (%s, %s, %s, %s)
        """, (title, image_url, price, ADMIN_EMAIL))

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFTs seeded"
    })

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)