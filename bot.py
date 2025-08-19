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
SENDER_SEED = os.getenv("WAVES_SEED")
AMOUNT_ASSET = os.getenv("AMOUNT_ASSET")
PRICE_ASSET = os.getenv("PRICE_ASSET")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
ORDER_NOTIONAL = int(os.getenv("ORDER_NOTIONAL", 25)) * 10**8  # WAVES amount in satoshi
GRID_LEVELS = int(os.getenv("GRID_LEVELS", 10))
GRID_SPACING_PCT = float(os.getenv("GRID_SPACING_PCT", 0.35)) / 100
REFRESH_SEC = int(os.getenv("REFRESH_SEC", 20))

if not SENDER_SEED:
    raise ValueError("Please set WAVES_SEED in environment variables!")

# ------------------------
# KEYS
# ------------------------
seed_bytes = SENDER_SEED.encode("utf-8")
private_key_bytes = blake2b(seed_bytes, digest_size=32).digest()
SENDER_KEY = SigningKey(private_key_bytes)
SENDER_PUBLIC_KEY = base58.b58encode(SENDER_KEY.verify_key.encode()).decode()

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
        "matcherPublicKey": SENDER_PUBLIC_KEY,
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
        b'\x00'
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
        "fee": 300000,
        "feeAssetId": None,
        "timestamp": ts,
        "proofs": []
    }

    body = (
        b'\x07' + b'\x02' +
        struct.pack(">q", ts) +
        struct.pack(">q", tx["amount"]) +
        struct.pack(">q", tx["price"]) +
        struct.pack(">q", tx["buyMatcherFee"]) +
        struct.pack(">q", tx["sellMatcherFee"]) +
        struct.pack(">q", tx["fee"]) +
        b'\x00'
    )

    tx["proofs"] = [sign_bytes(body)]
    return tx

# ------------------------
# BROADCAST
# ------------------------
def broadcast(tx):
    if DRY_RUN:
        print("DRY_RUN: would broadcast tx", tx)
        return {"status": "dry_run"}
    url = f"{NODE_URL}/transactions/broadcast"
    resp = requests.post(url, json=tx)
    return resp.json()

# ------------------------
# GRID GENERATION
# ------------------------
def generate_grid_orders(base_price):
    orders = []
    for i in range(1, GRID_LEVELS + 1):
        delta = int(base_price * GRID_SPACING_PCT * i)
        orders.append(build_order("buy", ORDER_NOTIONAL, base_price - delta))
        orders.append(build_order("sell", ORDER_NOTIONAL, base_price + delta))
    return orders

# ------------------------
# MAIN LOOP
# ------------------------
def main():
    BASE_PRICE = 150_000_000  # Example starting price, adjust dynamically if you want
    while True:
        print("Generating grid orders...")
        grid_orders = generate_grid_orders(BASE_PRICE)

        for i in range(0, len(grid_orders), 2):
            buy_order = grid_orders[i]
            sell_order = grid_orders[i + 1]

            exch_tx = build_exchange_tx(buy_order, sell_order, buy_order["price"], buy_order["amount"])
            result = broadcast(exch_tx)
            print(result)

        print(f"Sleeping {REFRESH_SEC} seconds...")
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    main()
