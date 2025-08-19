import os
import time
import struct
import base58
import requests
from nacl.signing import SigningKey

# ------------------------
# CONFIG
# ------------------------
NODE_URL = "https://nodes.wavesnodes.com"
MATCHER_URL = "https://matcher.waves.exchange"

SENDER_SEED = os.getenv("WAVES_SEED")
if not SENDER_SEED:
    raise ValueError("Please set WAVES_SEED in environment variables!")

SENDER_KEY = SigningKey(base58.b58decode(SENDER_SEED))
SENDER_PUBLIC_KEY = base58.b58encode(SENDER_KEY.verify_key.encode()).decode()

MATCHER_PUBLIC_KEY = os.getenv("MATCHER_PUBLIC_KEY")
if not MATCHER_PUBLIC_KEY:
    raise ValueError("Please set MATCHER_PUBLIC_KEY in environment variables!")

AMOUNT_ASSET = os.getenv("AMOUNT_ASSET")  # None or asset ID
PRICE_ASSET = os.getenv("PRICE_ASSET")    # None or asset ID

# ------------------------
# UTILITIES
# ------------------------
def b58(data: bytes) -> str:
    return base58.b58encode(data).decode()

def b58d(data: str) -> bytes:
    return base58.b58decode(data)

# ------------------------
# ORDER V3 SERIALIZATION
# ------------------------
def serialize_order(order):
    b = bytearray()
    b += b'\x03'  # version
    b += b58d(order["senderPublicKey"])
    b += b58d(order["matcherPublicKey"])

    # amountAsset
    if not order["assetPair"]["amountAsset"]:
        b += b'\x00'
    else:
        b += b'\x01' + b58d(order["assetPair"]["amountAsset"])

    # priceAsset
    if not order["assetPair"]["priceAsset"]:
        b += b'\x00'
    else:
        b += b'\x01' + b58d(order["assetPair"]["priceAsset"])

    # order type
    b += b'\x00' if order["orderType"] == "buy" else b'\x01'
    b += struct.pack(">q", order["price"])
    b += struct.pack(">q", order["amount"])
    b += struct.pack(">q", order["timestamp"])
    b += struct.pack(">q", order["expiration"])
    b += struct.pack(">q", order["matcherFee"])

    # matcher fee asset
    if "matcherFeeAssetId" in order and order["matcherFeeAssetId"]:
        if order["matcherFeeAssetId"].upper() != "WAVES":
            b += b'\x01' + b58d(order["matcherFeeAssetId"])
        else:
            b += b'\x00'
    else:
        b += b'\x00'

    return bytes(b)

def sign_order(order_bytes):
    return b58(SENDER_KEY.sign(order_bytes).signature)

# ------------------------
# PLACE ORDER
# ------------------------
def place_order(order):
    order_bytes = serialize_order(order)
    order["proofs"] = [sign_order(order_bytes)]
    order.pop("eip", None)

    amount = order["assetPair"]["amountAsset"] or ""
    price = order["assetPair"]["priceAsset"] or ""
    url = f"{MATCHER_URL}/matcher/orderbook/{amount}/{price}/orders"
    resp = requests.post(url, json=order)
    return resp.json()

# ------------------------
# MAIN FUNCTION
# ------------------------
def main():
    timestamp = int(time.time() * 1000)
    order = {
        "senderPublicKey": SENDER_PUBLIC_KEY,
        "matcherPublicKey": MATCHER_PUBLIC_KEY,
        "assetPair": {
            "amountAsset": AMOUNT_ASSET,
            "priceAsset": PRICE_ASSET
        },
        "orderType": "buy",
        "amount": 100000000,  # 1 WAVES
        "price": 150000000,   # 1.5 WAVES price
        "timestamp": timestamp,
        "expiration": timestamp + 24 * 60 * 60 * 1000,
        "matcherFee": 1000000,
        "matcherFeeAssetId": "WAVES"
    }

    result = place_order(order)
    print(result)

if __name__ == "__main__":
    main()
