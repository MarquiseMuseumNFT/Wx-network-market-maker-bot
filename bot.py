import base58
import hashlib
import json
import time
from nacl.signing import SigningKey

# Your keys
PRIVATE_KEY_BASE58 = "your_private_key_here"  # 32-byte seed in base58
PUBLIC_KEY_BASE58 = "8xihRrTTy6UiK82d2LWiSpaqyuiSs21AnjPG2y4FnxTH"

# Decode key
private_key = base58.b58decode(PRIVATE_KEY_BASE58)
signing_key = SigningKey(private_key)

def long_to_bytes(value, length=8):
    return value.to_bytes(length, byteorder="big", signed=False)

def blake2b256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()

def order_v3_to_bytes(order: dict) -> bytes:
    """
    Serialize order to bytes for signing (OrderV3 structure).
    """
    b = bytearray()
    b.append(order['version'])  # 1 byte
    b += base58.b58decode(order['senderPublicKey'])
    b += base58.b58decode(order['matcherPublicKey'])

    # AssetPair
    if order['assetPair']['amountAsset']:
        b.append(1)
        b += base58.b58decode(order['assetPair']['amountAsset'])
    else:
        b.append(0)

    if order['assetPair']['priceAsset']:
        b.append(1)
        b += base58.b58decode(order['assetPair']['priceAsset'])
    else:
        b.append(0)

    # Order type
    b.append(0 if order['orderType'] == "buy" else 1)

    # Price & Amount
    b += long_to_bytes(order['price'])
    b += long_to_bytes(order['amount'])

    # Timestamp, Expiration, Fee
    b += long_to_bytes(order['timestamp'])
    b += long_to_bytes(order['expiration'])
    b += long_to_bytes(order['matcherFee'])

    # Fee Asset
    if order['matcherFeeAssetId'] and order['matcherFeeAssetId'] != "WAVES":
        b.append(1)
        b += base58.b58decode(order['matcherFeeAssetId'])
    else:
        b.append(0)

    return bytes(b)

def sign_order(order: dict) -> dict:
    order_bytes = order_v3_to_bytes(order)
    # ✅ Sign the Blake2b256 hash of the bytes (fast mode)
    order_hash = blake2b256(order_bytes)
    signature = signing_key.sign(order_hash).signature
    order['proofs'] = [base58.b58encode(signature).decode()]
    return order

# Example order
order = {
    "version": 3,
    "senderPublicKey": PUBLIC_KEY_BASE58,
    "matcherPublicKey": "9cpfKN9suPNvfeUNphzxXMjcnn974eme8ZhWUjaktzU5",
    "assetPair": {
        "amountAsset": "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX",
        "priceAsset": "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"
    },
    "orderType": "sell",
    "price": 137011840,
    "amount": 2500000000,
    "timestamp": int(time.time() * 1000),
    "expiration": int(time.time() * 1000) + 24 * 60 * 60 * 1000,
    "matcherFee": 1_000_000,  # must be >= 0.01 WAVES = 1e6
    "matcherFeeAssetId": None  # or "WAVES"
}

signed_order = sign_order(order)

print("Final payload before sending:", json.dumps(signed_order, indent=2))
