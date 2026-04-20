from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import json

app = Flask(__name__)
CORS(app)

ADMIN_EMAIL = "mjessydk@gmail.com"
HOLD_HOURS = 12

DEPOSIT_WALLETS = {
    "BTC": "bc1qexamplebtcwalletaddress123456789",
    "ETH": "0xAbC1234567890Def1234567890AbCdEf12345678",
    "USDT": "TExampleUsdtWalletAddress123456789"
}

# Replace with your real OpenSea API key
OPENSEA_API_KEY = "5610dc0168674cedb954c0a9cb0c5433"

# Curated collections to make homepage feel busy
OPENSEA_COLLECTION_SLUGS = [
    "boredapeyachtclub",
    "pudgypenguins",
    "azuki",
    "doodles-official"
]


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nfts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        image_url TEXT NOT NULL,
        price TEXT NOT NULL,
        creator_email TEXT NOT NULL,
        holder_email TEXT,
        hold_status TEXT DEFAULT 'available',
        hold_until TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deposit_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nft_id INTEGER NOT NULL,
        nft_title TEXT NOT NULL,
        user_email TEXT NOT NULL,
        coin TEXT NOT NULL,
        amount TEXT NOT NULL,
        deposit_wallet TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        confirmed_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def expire_holds():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    now_iso = datetime.now().isoformat()

    cursor.execute("""
        UPDATE nfts
        SET hold_status = 'available',
            holder_email = NULL,
            hold_until = NULL
        WHERE hold_status = 'held'
          AND hold_until IS NOT NULL
          AND hold_until <= ?
    """, (now_iso,))

    conn.commit()
    conn.close()


def fetch_opensea_collection_nfts(slug: str, limit: int = 4):
    """
    OpenSea docs endpoint:
    GET https://api.opensea.io/api/v2/collection/{slug}/nfts
    """
    headers = {
        "accept": "application/json",
        "x-api-key": OPENSEA_API_KEY
    }

    url = f"https://api.opensea.io/api/v2/collection/{urllib.parse.quote(slug)}/nfts?limit={limit}"
    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("nfts", [])


init_db()


@app.route("/")
def home():
    expire_holds()
    return jsonify({"message": "iNFTCO backend is running"})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({
            "status": "error",
            "message": "All fields are required"
        }), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Registration successful for {username}"
        })
    except sqlite3.IntegrityError:
        return jsonify({
            "status": "error",
            "message": "Email already exists"
        }), 400


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email, password FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[3], password):
        return jsonify({
            "status": "success",
            "message": f"Login successful for {email}",
            "user": {
                "id": user[0],
                "username": user[1],
                "email": user[2]
            }
        })

    return jsonify({
        "status": "error",
        "message": "Invalid email or password"
    }), 401


@app.route("/api/create-nft", methods=["POST"])
def create_nft():
    data = request.get_json() or {}

    title = data.get("title")
    image_url = data.get("image_url")
    price = data.get("price")
    creator_email = data.get("creator_email")

    if not title or not image_url or not price or not creator_email:
        return jsonify({
            "status": "error",
            "message": "All NFT fields are required"
        }), 400

    if creator_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Only admin can create NFTs"
        }), 403

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO nfts (
            title,
            image_url,
            price,
            creator_email,
            holder_email,
            hold_status,
            hold_until
        )
        VALUES (?, ?, ?, ?, NULL, 'available', NULL)
    """, (title, image_url, price, creator_email))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "NFT created successfully"
    })


@app.route("/api/nfts", methods=["GET"])
def get_nfts():
    expire_holds()

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            title,
            image_url,
            price,
            creator_email,
            holder_email,
            hold_status,
            hold_until
        FROM nfts
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    nft_list = []
    for row in rows:
        nft_list.append({
            "id": row[0],
            "title": row[1],
            "image_url": row[2],
            "price": row[3],
            "creator_email": row[4],
            "holder_email": row[5],
            "hold_status": row[6] or "available",
            "hold_until": row[7]
        })

    return jsonify({
        "status": "success",
        "nfts": nft_list,
        "deposit_wallets": DEPOSIT_WALLETS
    })


@app.route("/api/create-deposit-request", methods=["POST"])
def create_deposit_request():
    expire_holds()

    data = request.get_json() or {}

    nft_id = data.get("nft_id")
    user_email = data.get("user_email")
    coin = data.get("coin")

    if not nft_id or not user_email or not coin:
        return jsonify({
            "status": "error",
            "message": "Missing deposit request data"
        }), 400

    coin = coin.upper()

    if coin not in DEPOSIT_WALLETS:
        return jsonify({
            "status": "error",
            "message": "Unsupported coin"
        }), 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, price, hold_status, hold_until
        FROM nfts
        WHERE id = ?
    """, (nft_id,))
    nft = cursor.fetchone()

    if not nft:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "NFT not found"
        }), 404

    _, nft_title, nft_price, hold_status, hold_until = nft

    if hold_status == "held" and hold_until:
        expiry = datetime.fromisoformat(hold_until)
        if datetime.now() < expiry:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "NFT is currently held"
            }), 400

    cursor.execute("""
        SELECT id FROM deposit_requests
        WHERE nft_id = ? AND user_email = ? AND status = 'pending'
    """, (nft_id, user_email))
    existing_request = cursor.fetchone()

    if existing_request:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "You already have a pending deposit request for this NFT"
        }), 400

    deposit_wallet = DEPOSIT_WALLETS[coin]

    cursor.execute("""
        INSERT INTO deposit_requests (
            nft_id,
            nft_title,
            user_email,
            coin,
            amount,
            deposit_wallet,
            status,
            created_at,
            confirmed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, NULL)
    """, (
        nft_id,
        nft_title,
        user_email,
        coin,
        nft_price,
        deposit_wallet,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request submitted. Waiting for admin confirmation.",
        "deposit_wallet": deposit_wallet,
        "amount": nft_price,
        "coin": coin
    })


@app.route("/api/pending-deposits", methods=["GET"])
def pending_deposits():
    expire_holds()

    user_email = request.args.get("user_email")
    if user_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required"
        }), 403

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            nft_id,
            nft_title,
            user_email,
            coin,
            amount,
            deposit_wallet,
            status,
            created_at,
            confirmed_at
        FROM deposit_requests
        WHERE status = 'pending'
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    deposits = []
    for row in rows:
        deposits.append({
            "id": row[0],
            "nft_id": row[1],
            "nft_title": row[2],
            "user_email": row[3],
            "coin": row[4],
            "amount": row[5],
            "deposit_wallet": row[6],
            "status": row[7],
            "created_at": row[8],
            "confirmed_at": row[9]
        })

    return jsonify({
        "status": "success",
        "deposits": deposits
    })


@app.route("/api/confirm-deposit", methods=["POST"])
def confirm_deposit():
    expire_holds()

    data = request.get_json() or {}

    deposit_id = data.get("deposit_id")
    admin_email = data.get("admin_email")

    if admin_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required"
        }), 403

    if not deposit_id:
        return jsonify({
            "status": "error",
            "message": "Missing deposit id"
        }), 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nft_id, user_email, status
        FROM deposit_requests
        WHERE id = ?
    """, (deposit_id,))
    deposit = cursor.fetchone()

    if not deposit:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request not found"
        }), 404

    _, nft_id, user_email, deposit_status = deposit

    if deposit_status != "pending":
        conn.close()
        return jsonify({
            "status": "error",
            "message": "Deposit request is not pending"
        }), 400

    cursor.execute("""
        SELECT hold_status, hold_until
        FROM nfts
        WHERE id = ?
    """, (nft_id,))
    nft = cursor.fetchone()

    if not nft:
        conn.close()
        return jsonify({
            "status": "error",
            "message": "NFT not found"
        }), 404

    hold_status, hold_until = nft

    if hold_status == "held" and hold_until:
        expiry = datetime.fromisoformat(hold_until)
        if datetime.now() < expiry:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "NFT is already held"
            }), 400

    new_hold_until = datetime.now() + timedelta(hours=HOLD_HOURS)

    cursor.execute("""
        UPDATE nfts
        SET holder_email = ?,
            hold_status = 'held',
            hold_until = ?
        WHERE id = ?
    """, (user_email, new_hold_until.isoformat(), nft_id))

    cursor.execute("""
        UPDATE deposit_requests
        SET status = 'confirmed',
            confirmed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), deposit_id))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": f"Deposit confirmed. NFT held for {HOLD_HOURS} hours."
    })


@app.route("/api/reject-deposit", methods=["POST"])
def reject_deposit():
    data = request.get_json() or {}

    deposit_id = data.get("deposit_id")
    admin_email = data.get("admin_email")

    if admin_email != ADMIN_EMAIL:
        return jsonify({
            "status": "error",
            "message": "Admin access required"
        }), 403

    if not deposit_id:
        return jsonify({
            "status": "error",
            "message": "Missing deposit id"
        }), 400

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE deposit_requests
        SET status = 'rejected',
            confirmed_at = ?
        WHERE id = ? AND status = 'pending'
    """, (datetime.now().isoformat(), deposit_id))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Deposit request rejected."
    })


@app.route("/api/external-nfts", methods=["GET"])
def get_external_nfts():
    all_nfts = []

    if not OPENSEA_API_KEY or OPENSEA_API_KEY == "PUT_YOUR_OPENSEA_API_KEY_HERE":
        return jsonify({
            "status": "success",
            "external_nfts": []
        })

    for slug in OPENSEA_COLLECTION_SLUGS:
        try:
            nfts = fetch_opensea_collection_nfts(slug, limit=4)

            for nft in nfts:
                image_url = (
                    nft.get("image_url")
                    or nft.get("display_image_url")
                    or nft.get("image_original_url")
                )

                identifier = nft.get("identifier")
                contract = nft.get("contract")
                opensea_url = nft.get("opensea_url")

                if not opensea_url and contract and identifier:
                    opensea_url = f"https://opensea.io/assets/ethereum/{contract}/{identifier}"

                all_nfts.append({
                    "title": nft.get("name") or f"{slug} #{identifier}",
                    "image_url": image_url,
                    "link": opensea_url or "https://opensea.io/",
                    "source": slug
                })

        except Exception as e:
            print(f"Error loading OpenSea collection {slug}: {e}")

    return jsonify({
        "status": "success",
        "external_nfts": all_nfts
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)