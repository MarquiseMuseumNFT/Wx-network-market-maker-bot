#!/usr/bin/env python3
import os, time, json, base64, base58, hashlib, requests, struct
from nacl.signing import SigningKey

# ===============================
# Config (via environment)
# ===============================
SEED       = os.environ.get("WAVES_SEED", "").encode()
NODE       = os.environ.get("WAVES_NODE",   "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER",   "https://matcher.wx.network")

GRID_LEVELS      = int(os.environ.get("GRID_LEVELS", 10))
GRID_SPACING_PCT = float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL   = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC      = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN          = os.environ.get("DRY_RUN", "false").lower() == "true"

ASSET1 = os.environ.get("AMOUNT_ASSET", "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX")
ASSET2 = os.environ.get("PRICE_ASSET",  "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA")
MATCHER_FEE_ASSET_ID = os.environ.get("MATCHER_FEE_ASSET_ID", "WAVES")

# ===============================
# Keys
# ===============================
def _derive_sk_from_seed(seed_bytes: bytes) -> SigningKey:
    if not seed_bytes:
        raise RuntimeError("Missing WAVES_SEED in environment.")
    seed_hash = hashlib.blake2b(seed_bytes, digest_size=32).digest()
    return SigningKey(seed_hash)

sk = _derive_sk_from_seed(SEED)
pk = sk.verify_key
PUBKEY_B58 = base58.b58encode(pk.encode()).decode()  # for matcher API

def now_ms() -> int:
    return int(time.time() * 1000)

ADDRESS = "3PFYpLMMQBDBecjHxb18zaWPy4N52anweGn"
print("Using address:", ADDRESS)

# ===============================
# Matcher public key
# ===============================
def get_matcher_pk() -> str:
    r = requests.get(f"{MATCHER}/matcher", timeout=10)
    r.raise_for_status()
    return r.text.strip().strip('"')

MATCHER_PUBKEY = get_matcher_pk()
print("Matcher pubkey:", MATCHER_PUBKEY)

# ===============================
# Order serialization & signing
# ===============================
def _pack_long(x: int) -> bytes:
    return struct.pack(">q", int(x))

def _asset_id_bytes(asset_id: str) -> bytes:
    if not asset_id or asset_id.upper() == "WAVES":
        return b"\x00"
    return b"\x01" + base58.b58decode(asset_id)

def order_v3_bytes(order: dict) -> bytes:
    b = bytearray()
    b += b"\x03"
    b += base58.b58decode(order["senderPublicKey"])
    b += base58.b58decode(order["matcherPublicKey"])
    b += _asset_id_bytes(order["assetPair"]["amountAsset"])
    b += _asset_id_bytes(order["assetPair"]["priceAsset"])
    b += b"\x00" if order["orderType"] == "buy" else b"\x01"
    b += _pack_long(order["price"])
    b += _pack_long(order["amount"])
    b += _pack_long(order["timestamp"])
    b += _pack_long(order["expiration"])
    b += _pack_long(order["matcherFee"])
    if order.get("matcherFeeAssetId"):
        b += _asset_id_bytes(order["matcherFeeAssetId"])
    else:
        b += b"\x00"
    return bytes(b)

def sign_order_b58(order: dict) -> str:
    msg = order_v3_bytes(order)
    sig = sk.sign(msg).signature
    return base58.b58encode(sig).decode()

ALLOWED_ORDER_KEYS = {
    "senderPublicKey", "matcherPublicKey", "assetPair", "orderType",
    "amount", "price", "timestamp", "expiration", "matcherFee",
    "version", "proofs", "matcherFeeAssetId"
}

def wl(d: dict, allowed: set) -> dict:
    return {k: v for k, v in d.items() if k in allowed}

# ===============================
# Post order
# ===============================
def post_order(payload: dict):
    url = f"{MATCHER}/matcher/orderbook"
    try:
        r = requests.post(url, json=payload, timeout=15)
        print(f"Order resp: {r.status_code} {r.text}")
        ctype = r.headers.get("Content-Type", "")
        return r.json() if "application/json" in ctype else r.text
    except Exception as e:
        print("Order post exception:", repr(e))
        raise

# ===============================
# Asset decimals
# ===============================
def get_asset_decimals(asset_id: str) -> int:
    if asset_id.upper() == "WAVES":
        return 8
    r = requests.get(f"{NODE}/assets/details/{asset_id}", timeout=10)
    r.raise_for_status()
    return int(r.json()["decimals"])

AMOUNT_DECIMALS = get_asset_decimals(ASSET1)
PRICE_DECIMALS  = get_asset_decimals(ASSET2)
print(f"Decimals: amount={AMOUNT_DECIMALS}, price={PRICE_DECIMALS}")

# ===============================
# Orders management
# ===============================
def get_my_orders():
    r = requests.get(f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/address/{ADDRESS}/active", timeout=10)
    r.raise_for_status()
    return r.json()

def cancel_order(order_id):
    payload = {"orderId": order_id, "sender": ADDRESS}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return True
    r = requests.post(f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel", json=payload, timeout=10)
    print("Cancel resp:", r.status_code, r.text)
    return r.json()

def cancel_all():
    try:
        orders = get_my_orders()
        if not orders:
            print("No active orders to cancel")
            return
        for o in orders:
            cancel_order(o["id"])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("No active orders to cancel")
        else:
            print("Cancel error:", e)

# ===============================
# Place order
# ===============================
def place_order(amount_units: float, price_quote: float, side: str):
    amount = int(round(amount_units * 10**AMOUNT_DECIMALS))
    price  = int(round(price_quote * 10**(8 + PRICE_DECIMALS - AMOUNT_DECIMALS)))

    order_core = {
        "version": 3,
        "senderPublicKey": PUBKEY_B58,
        "matcherPublicKey": MATCHER_PUBKEY,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
        "orderType": side,
        "price": price,
        "amount": amount,
        "timestamp": now_ms(),
        "expiration": now_ms() + 24 * 60 * 60 * 1000,
        "matcherFee": 1000000,
    }

    if MATCHER_FEE_ASSET_ID.upper() != "WAVES":
        order_core["matcherFeeAssetId"] = MATCHER_FEE_ASSET_ID

    proof_b58 = sign_order_b58(order_core)
    order_core["proofs"] = [proof_b58]

    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_quote} | Proof b58: {proof_b58}")
        return False

    return post_order(final_payload)

# ===============================
# Price feeds
# ===============================
def get_htx_price():
    r = requests.get("https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt", timeout=8)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    r = requests.get(f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}", timeout=8)
    r.raise_for_status()
    ob = r.json()
    bid = float(ob["bids"][0]["price"])
    ask = float(ob["asks"][0]["price"])
    return (bid + ask) / 2e8

def get_price():
    try:
        return get_htx_price()
    except Exception as e:
        print("HTX feed failed, fallback to WX mid →", e)
        return get_wx_mid()

# ===============================
# Strategy loop
# ===============================
def run():
    while True:
        try:
            cancel_all()
            mid = get_price()
            print(f"Mid price used: {mid}")

            step = mid * (GRID_SPACING_PCT / 100.0)
            for i in range(1, GRID_LEVELS + 1):
                p_buy  = mid - i * step
                p_sell = mid + i * step
                place_order(ORDER_NOTIONAL, p_buy, "buy")
                place_order(ORDER_NOTIONAL, p_sell, "sell")

        except Exception as e:
            print("Main loop exception:", e)
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()
