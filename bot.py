import requests
import base58
import struct
from nacl.signing import SigningKey

# ------------------------
# CONFIGURATION
# ------------------------
NODE_URL = "https://nodes.wavesnodes.com"
MATCHER_URL = "https://matcher.waves.exchange"
SENDER_SEED = "your seed phrase here"
SENDER_KEY = SigningKey(base58.b58decode(base58.b58encode(Signer(SENDER_SEED).private_key))))

# ------------------------
# UTILITIES
# ------------------------
def base58_encode(data: bytes) -> str:
    return base58.b58encode(data).decode()

def base58_decode(data: str) -> bytes:
    return base58.b58decode(data)

# ------------------------
# ORDER SERIALIZATION
# ------------------------
def order_v3_bytes(order):
    b = bytearray()
    b += b'\x03'  # Version 3
    b += base58_decode(order["senderPublicKey"])
    b += base58_decode(order["matcherPublicKey"])
    
    # Amount asset
    if not order["assetPair"]["amountAsset"] or order["assetPair"]["amountAsset"].upper() == "WAVES":
        b += b'\x00'
    else:
        b += b'\x01' + base58_decode(order["assetPair"]["amountAsset"])
    
    # Price asset
    if not order["assetPair"]["priceAsset"] or order["assetPair"]["priceAsset"].upper() == "WAVES":
        b += b'\x00'
    else:
        b += b'\x01' + base58_decode(order["assetPair"]["priceAsset"])
    
    b += b'\x00' if order["orderType"] == "buy" else b'\x01'
    b += struct.pack(">q", order["price"])
    b += struct.pack(">q", order["amount"])
    b += struct.pack(">q", order["timestamp"])
    b += struct.pack(">q", order["expiration"])
    b += struct.pack(">q", order["matcherFee"])
    
    # Matcher fee asset
    if "matcherFeeAssetId" in order and order["matcherFeeAssetId"].upper() != "WAVES":
        b += b'\x01' + base58_decode(order["matcherFeeAssetId"])
    else:
        b += b'\x00'
    
    return bytes(b)

def sign_order(order_bytes):
    signature = SENDER_KEY.sign(order_bytes).signature
    return base58_encode(signature)

# ------------------------
# ORDER PLACEMENT
# ------------------------
def place_order(order):
    order_bytes = order_v3_bytes(order)
    order["proofs"] = [sign_order(order_bytes)]
    order.pop("eip", None)  # remove EIP if present
    
    url = f"{MATCHER_URL}/matcher/orderbook/{order['assetPair']['amountAsset']}/{order['assetPair']['priceAsset']}/order"
    resp = requests.post(url, json=order)
    return resp.json()

# ------------------------
# EXAMPLE USAGE
# ------------------------
def main():
    order = {
        "senderPublicKey": base58_encode(SENDER_KEY.verify_key.encode()),
        "matcherPublicKey": "matcher public key here",
        "assetPair": {
            "amountAsset": None,  # WAVES
            "priceAsset": None    # WAVES
        },
        "orderType": "buy",
        "amount": 100000000,       # 1 WAVES
        "price": 150000000,        # 1.5 WAVES price
        "timestamp": 1755570213127,
        "expiration": 1755656613127,
        "matcherFee": 1000000,
        "matcherFeeAssetId": "WAVES"
    }

    result = place_order(order)
    print(result)

if __name__ == "__main__":
    main()
