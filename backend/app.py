import os
import json
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

# =========================
# DATABASE CONNECTION
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

# =========================
# INIT DATABASE
# =========================
def init_db():
    conn = get_db()
    cur = conn.cursor()

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

# =========================
# ROUTES
# =========================

# Health check
@app.route("/")
def home():
    return jsonify({"message": "NFT Web3 backend is live", "status": "running"})

# Get NFTs
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

# Add NFT (Admin only)
@app.route("/api/nfts", methods=["POST"])
def add_nft():
    data = request.json

    name = data.get("name")
    image = data.get("image")
    price = data.get("price", "0.1 ETH")
    holdable = data.get("holdable", True)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO nfts (name, image, price, holdable)
        VALUES (%s, %s, %s, %s)
        RETURNING *;
    """, (name, image, price, holdable))

    new_nft = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return jsonify(new_nft)

# =========================
# RUN (LOCAL ONLY)
# =========================
if __name__ == "__main__":
    app.run(debug=True)