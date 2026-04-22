import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row

app = Flask(__name__)
CORS(app)

ADMIN_EMAIL = "mjessydk@gmail.com"

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xExampleEthereumWalletAddress1234567890",
    "USDT": "TExampleUSDTWalletAddress1234567890"
}

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT,
            email TEXT UNIQUE,
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS nfts (
            id SERIAL PRIMARY KEY,
            name TEXT,
            image TEXT,
            price TEXT,
            holdable BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route("/")
def home():
    return jsonify({"message": "NFT Web3 backend is live", "status": "running"})

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

@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM nfts ORDER BY id DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    nfts = []
    for row in rows:
        nfts.append({
            "id": row["id"],
            "title": row["name"],
            "image_url": row["image"],
            "price": row["price"],
            "hold_status": "available",
            "created_at": str(row["created_at"]) if row.get("created_at") else None
        })

    return jsonify({
        "deposit_wallets": DEPOSIT_WALLETS,
        "nfts": nfts
    })

@app.route("/api/nfts", methods=["POST"])
def add_nft():
    data = request.json or {}

    name = (data.get("name") or "").strip()
    image = (data.get("image") or "").strip()
    price = (data.get("price") or "").strip()
    holdable = data.get("holdable", True)

    if not name or not image or not price:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (name, image, price, holdable)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """, (name, image, price, holdable))

    nft = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created",
        "nft": {
            "id": nft["id"],
            "title": nft["name"],
            "image_url": nft["image"],
            "price": nft["price"]
        }
    })

@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.json or {}

    title = (data.get("title") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    price = (data.get("price") or "").strip()
    creator_email = (data.get("creator_email") or "").strip().lower()

    if creator_email != ADMIN_EMAIL.lower():
        return jsonify({
            "status": "error",
            "message": "Not authorized"
        }), 403

    if not title or not image_url or not price:
        return jsonify({
            "status": "error",
            "message": "Missing required fields"
        }), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (name, image, price, holdable)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """, (title, image_url, price, True))

    nft = cur.fetchone()
    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created",
        "nft": {
            "id": nft["id"],
            "title": nft["name"],
            "image_url": nft["image"],
            "price": nft["price"]
        }
    })

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
    return jsonify({"status": "success", "external_nfts": fallback})

@app.route("/api/seed-nfts", methods=["GET"])
def seed_nfts():
    conn = get_db()
    cur = conn.cursor()

    sample_nfts = [
        ("Neon Panther Genesis", "https://images.unsplash.com/photo-1614850523459-c2f4c699c52c", "0.42", True),
        ("Cyber Mask #12", "https://images.unsplash.com/photo-1642104704074-907c0698cbd9", "0.65", True),
        ("Galaxy Ape Prime", "https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4", "0.88", True),
        ("Royal Skull Vault", "https://images.unsplash.com/photo-1545239351-1141bd82e8a6", "1.10", True),
        ("Meta Samurai", "https://images.unsplash.com/photo-1642425149556-b6f6c1f9b1d4", "0.73", True),
        ("Glitch Lion X", "https://images.unsplash.com/photo-1516321318423-f06f85e504b3", "1.25", True)
    ]

    for nft in sample_nfts:
        cur.execute("""
            INSERT INTO nfts (name, image, price, holdable)
            VALUES (%s, %s, %s, %s)
        """, nft)

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFTs seeded"
    })

if __name__ == "__main__":
    app.run(debug=True)