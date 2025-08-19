import os
import time
import struct
import base58
import requests
from hashlib import blake2b
from nacl.signing import SigningKey

# ------------------------
# CONFIG
# ------------------------
NODE_URL = os.getenv("WAVES_NODE", "https://nodes.wavesnodes.com")

# Seed phrase from environment
SENDER_SEED = os.getenv("WAVES_SEED")
if not SENDER_SEED:
    raise ValueError("Please set WAVES_SEED in environment variables!")

# Derive 32-byte private key from seed phrase
seed_bytes = SENDER_SEED.encode("utf-8")
private_key_bytes = blake2b(seed_bytes, digest_size=32).digest()
SENDER_KEY = SigningKey(private_key_bytes)
SENDER_PUBLIC_KEY = base58.b58encode(SENDER_KEY.verify_key.encode()).decode()

# Assets
AMOUNT_ASSET = os.getenv("AMOUNT_ASSET")   # 9RVj...
PRICE_ASSET  = os.getenv("PRICE_ASSET")    # Eikm...

# ------------------------
# UTILITIES
# ------------------------
def b58(data: bytes) -> str:
    return base58.b58encode(data).decode()

def b58d(data: str) -> bytes:
    return base58.b58decode(data)

def sign_bytes(data: bytes) -> str:
    return b58(SENDER_KEY.sign(data).signature)

# ------------------------
# CREATE ORDER V3
# ------------------------
def build_order(order_type, amount, price, matcher_fee=1000000, validity=24*60*60*1000):
    ts = int(time.time() * 1000)
    order = {
        "version": 3,
        "senderPublicKey": SENDER_PUBLIC_KEY,
        "matcherPublicKey": SENDER_PUBLIC_KEY,  # since no matcher, we use self
        "assetPair": {"amountAsset": AMOUNT_ASSET, "priceAsset": PRICE_ASSET},
        "orderType": order_type,
        "amount": amount,
        "price": price,
        "timestamp": ts,
        "expiration": ts + validity,
        "matcherFee": matcher_fee,
        "matcherFeeAssetId": "WAVES",
        "proofs": []
    }

    # Simplified serialization for signing
    body = (
        b'\x03' +
        b58d(order["senderPublicKey"]) +
        b58d(order["matcherPublicKey"]) +
        (b'\x01' + b58d(AMOUNT_ASSET)) +
        (b'\x01' + b58d(PRICE_ASSET)) +
        (b'\x00' if order_type == "buy" else b'\x01') +
        struct.pack(">q", price) +
        struct.pack(">q", amount) +
        struct.pack(">q", ts) +
        struct.pack(">q", order["expiration"]) +
        struct.pack(">q", matcher_fee) +
        b'\x00'  # matcherFeeAsset=WAVES
    )

    order["proofs"] = [sign_bytes(body)]
    return order

# ------------------------
# EXCHANGE TX V2
# ------------------------
def build_exchange_tx(order1, order2, price, amount):
    ts = int(time.time() * 1000)
    tx = {
        "type": 7,
        "version": 2,
        "order1": order1,
        "order2": order2,
        "price": price,
        "amount": amount,
        "buyMatcherFee": order1["matcherFee"],
        "sellMatcherFee": order2["matcherFee"],
        "fee": 300000,  # flat fee
        "feeAssetId": None,
        "timestamp": ts,
        "proofs": []
    }

    # Minimal serialization for signing
    body = (
        b'\x07' + b'\x02' +
        struct.pack(">q", ts) +
        struct.pack(">q", tx["amount"]) +
        struct.pack(">q", tx["price"]) +
        struct.pack(">q", tx["buyMatcherFee"]) +
        struct.pack(">q", tx["sellMatcherFee"]) +
        struct.pack(">q", tx["fee"]) +
        b'\x00'  # feeAsset=WAVES
    )

    tx["proofs"] = [sign_bytes(body)]
    return tx

# ------------------------
# BROADCAST
# ------------------------
def broadcast(tx):
    url = f"{NODE_URL}/transactions/broadcast"
    resp = requests.post(url, json=tx)
    return resp.json()

# ------------------------
# MAIN
# ------------------------
def main():
    # Example: self-matching order (buy + sell)
    buy_order  = build_order("buy", 100_000_000, 150_000_000)
    sell_order = build_order("sell", 100_000_000, 150_000_000)

    exch_tx = build_exchange_tx(buy_order, sell_order, 150_000_000, 100_000_000)

    result = broadcast(exch_tx)
    print(result)

if __name__ == "__main__":
    main()
