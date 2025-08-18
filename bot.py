#!/usr/bin/env python3
import os, time, json, base58, hashlib, requests, struct
from nacl.signing import SigningKey
from nacl.hash import blake2b
from nacl.encoding import RawEncoder

# ===============================
# Config (via environment)
# ===============================
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE",   "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER",   "https://matcher.wx.network")

GRID_LEVELS      = int(os.environ.get("GRID_LEVELS", 10))
GRID_SPACING_PCT = float(os.environ.get("GRID_SPACING_PCT", 0.35))  # % spacing between grid levels
ORDER_NOTIONAL   = float(os.environ.get("ORDER_NOTIONAL", 25))       # base units per order
REFRESH_SEC      = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN          = os.environ.get("DRY_RUN", "false").lower() == "true"

# Pair (amountAsset/priceAsset)
ASSET1 = os.environ.get("AMOUNT_ASSET", "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX")
ASSET2 = os.environ.get("PRICE_ASSET",  "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA")

# Explicitly choose fee asset (default WAVES)
MATCHER_FEE_ASSET_ID = os.environ.get("MATCHER_FEE_ASSET_ID", "WAVES")  # "WAVES" or base58 asset id

# ===============================
# Keys
# ===============================
# Derive a deterministic signing key from SEED (simple hash → ed25519)
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

def now_ms() -> int:
    return int(time.time() * 1000)

def blake2b256(data: bytes) -> bytes:
    return blake2b(data, digest_size=32, encoder=RawEncoder)

# ===============================
# Address / Matcher PK
# ===============================
def resolve_address_from_node(pubkey_b58: str) -> str:
    url = f"{NODE}/addresses/publicKey/{pubkey_b58}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text.strip().strip('"')

def get_matcher_pk() -> str:
    url = f"{MATCHER}/matcher"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text.strip().strip('"')

try:
    ADDRESS = resolve_address_from_node(PUBKEY)
    MATCHER_PUBKEY = get_matcher_pk()
except Exception as e:
    print("Startup failure (address/matcher pk):", e)
    raise

# ===============================
# Order v3 binary serializer
# ===============================
def _pack_long(x: int) -> bytes:
    # Waves uses signed 64-bit big endian
    return struct.pack(">q", int(x))

def _asset_id_bytes(asset_id: str) -> bytes:
    """
    For asset references in Order/AssetPair/MatcherFeeAsset:
    - WAVES: single byte 0x00
    - Other asset: 0x01 + 32 bytes of assetId
    """
    if asset_id is None or asset_id == "" or asset_id.upper() == "WAVES":
        return b"\x00"
    return b"\x01" + base58.b58decode(asset_id)

def _asset_pair_bytes(amount_asset: str, price_asset: str) -> bytes:
    return _asset_id_bytes(amount_asset) + _asset_id_bytes(price_asset)

def order_v3_bytes(order: dict) -> bytes:
    """
    Binary layout (Order V3):
      [0] version: 1 byte (0x03)
      [1] senderPublicKey: 32 bytes
      [2] matcherPublicKey: 32 bytes
      [3] assetPair:
            amountAsset: (0x00) or (0x01 + 32b)
            priceAsset:  (0x00) or (0x01 + 32b)
      [4] orderType: 1 byte (0 = BUY, 1 = SELL)
      [5] price: int64 (be)
      [6] amount: int64 (be)
      [7] timestamp: int64 (be)
      [8] expiration: int64 (be)
      [9] matcherFee: int64 (be)
     [10] matcherFeeAssetId: (0x00) or (0x01 + 32b)
    """
    b = bytearray()
    b += b"\x03"  # version
    b += base58.b58decode(order["senderPublicKey"])
    b += base58.b58decode(order["matcherPublicKey"])
    b += _asset_pair_bytes(order["assetPair"]["amountAsset"], order["assetPair"]["priceAsset"])
    b += (b"\x00" if order["orderType"] == "buy" else b"\x01")
    b += _pack_long(order["price"])
    b += _pack_long(order["amount"])
    b += _pack_long(order["timestamp"])
    b += _pack_long(order["expiration"])
    b += _pack_long(order["matcherFee"])
    fee_asset = order.get("matcherFeeAssetId", "WAVES")
    b += _asset_id_bytes(fee_asset)
    return bytes(b)

def sign_order_proof(order: dict) -> str:
    msg = order_v3_bytes(order)
    digest = blake2b256(msg)
    sig = sk.sign(digest).signature
    return base58.b58encode(sig).decode()

# ===============================
# Posting / helpers
# ===============================
ALLOWED_ORDER_KEYS = {
    "senderPublicKey", "matcherPublicKey", "assetPair", "orderType",
    "amount", "price", "timestamp", "expiration", "matcherFee",
    "version", "proofs", "matcherFeeAssetId"
}

def wl(d: dict, allowed: set) -> dict:
    return {k: v for k, v in d.items() if k in allowed}

def post_order(payload: dict):
    url = f"{MATCHER}/matcher/orderbook"
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"Order resp: {r.status_code} {r.text}")
        return r.json() if r.headers.get("Content-Type", "").startswith("application/json") else r.text
    except Exception as e:
        print("Order post exception:", repr(e))
        raise

# ===============================
# Price feeds
# ===============================
def get_htx_price():
    url = "https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    ob = r.json()
    bid = float(ob["bids"][0]["price"])
    ask = float(ob["asks"][0]["price"])
    return (bid + ask) / 1e8

def get_price():
    try:
        return get_htx_price()
    except Exception as e:
        print("HTX feed failed, fallback to WX mid →", e)
        return get_wx_mid()

# ===============================
# Active orders & cancellation
# ===============================
def get_my_orders():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/address/{ADDRESS}/active"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def cancel_order(order_id):
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel"
    payload = {"orderId": order_id, "sender": ADDRESS}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return True
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Cancel resp:", r.status_code, r.text)
        return r.json() if "application/json" in r.headers.get("Content-Type", "") else r.text
    except Exception as e:
        print("Cancel error:", repr(e))
        return None

def cancel_all():
    try:
        orders = get_my_orders()
        for o in orders:
            cancel_order(o["id"])
    except Exception as e:
        print("Cancel error (listing active orders):", e)

# ===============================
# Place order (v3 + proper signing)
# ===============================
def place_order(amount_units: float, price_quote: float, side: str):
    order_core = {
        "version": 3,
        "senderPublicKey": PUBKEY,
        "matcherPublicKey": MATCHER_PUBKEY,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
        "orderType": side,  # "buy" or "sell"
        "price": int(round(price_quote * 10**8)),
        "amount": int(round(amount_units * 10**8)),
        "timestamp": now_ms(),
        "expiration": now_ms() + 24 * 60 * 60 * 1000,
        "matcherFee": 300000,  # 0.003 WAVES
        "matcherFeeAssetId": MATCHER_FEE_ASSET_ID,  # serialize as WAVES (0x00) by default
    }

    proof = sign_order_proof(order_core)
    order_core["proofs"] = [proof]

    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    print("Sending keys:", sorted(final_payload.keys()))
    print("Final payload before sending:", final_payload)

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_quote}")
        return True

    return post_order(final_payload)

# ===============================
# Strategy loop
# ===============================
def run():
    while True:
        try:
            # clear existing grid
            cancel_all()

            mid = get_price()
            print(f"Mid price used: {mid}")

            step = mid * (GRID_SPACING_PCT / 100.0)
            for i in range(1, GRID_LEVELS + 1):
                p_buy  = mid - i * step
                p_sell = mid + i * step
                place_order(ORDER_NOTIONAL, p_buy,  "buy")
                place_order(ORDER_NOTIONAL, p_sell, "sell")

        except Exception as e:
            print("Error in main loop:", repr(e))

        time.sleep(REFRESH_SEC)

# ===============================
# Entry
# ===============================
if __name__ == "__main__":
    run()
