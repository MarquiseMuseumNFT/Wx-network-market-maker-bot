#!/usr/bin/env python3
import os, time, json, base58, hashlib, requests
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

# ===============================
# Keys
# ===============================
# Derive a deterministic signing key from SEED
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

def now_ms() -> int:
    return int(time.time() * 1000)

def blake2b256(data: bytes) -> bytes:
    return blake2b(data, digest_size=32, encoder=RawEncoder)

# ===============================
# Address (for /address/... endpoints and cancel payload)
# ===============================
def resolve_address_from_node(pubkey_b58: str) -> str:
    """
    Fetch address from node for given public key to avoid manual derivation pitfalls.
    """
    url = f"{NODE}/addresses/publicKey/{pubkey_b58}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.text.strip().strip('"')

try:
    ADDRESS = resolve_address_from_node(PUBKEY)
except Exception as e:
    print("Failed to resolve address from node:", e)
    # If node lookup fails, hard-stop to prevent 404 churn
    raise

# ===============================
# Safety / Signing helpers
# ===============================
def ensure_no_matcher_pk(d: dict):
    if "matcherPublicKey" in d:
        raise RuntimeError("matcherPublicKey found in payload!")

ALLOWED_ORDER_KEYS = {
    "senderPublicKey", "assetPair", "orderType", "amount", "price",
    "timestamp", "expiration", "matcherFee", "version", "proofs"
}

def wl(d: dict, allowed: set) -> dict:
    """Whitelist keys for final payload."""
    return {k: v for k, v in d.items() if k in allowed}

def sign_order_proof(order: dict) -> str:
    """
    Local signing: we hash the compact JSON (blake2b-256) and sign the digest.
    Proof is base58-encoded signature. We do NOT add matcherPublicKey anywhere.
    """
    raw = json.dumps(order, separators=(",", ":"), ensure_ascii=False).encode()
    digest = blake2b256(raw)
    sig = sk.sign(digest).signature
    return base58.b58encode(sig).decode()

def post_order(payload: dict):
    url = f"{MATCHER}/matcher/orderbook"
    try:
        r = requests.post(url, json=payload, timeout=15)
        # Log both status code and text for easier debugging
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
    return (bid + ask) / 2 / 1e8

def get_price():
    try:
        return get_htx_price()
    except Exception as e:
        print("HTX feed failed, fallback to WX mid →", e)
        return get_wx_mid()

# ===============================
# Active orders & cancellation
# (Use address to avoid 404 on pubkey endpoint)
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
# >>> Place order (your corrected version, plus strict guards)
# ===============================
def place_order(amount_units: float, price_quote: float, side: str):
    order_core = {
        "senderPublicKey": PUBKEY,
        "amount": int(round(amount_units * 10**8)),
        "price": int(round(price_quote * 10**8)),
        "orderType": side,  # "buy" or "sell"
        "matcherFee": 300000,
        "version": 3,
        "timestamp": now_ms(),
        "expiration": now_ms() + 24 * 60 * 60 * 1000,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
    }

    # Ensure matcherPublicKey is not included anywhere
    ensure_no_matcher_pk(order_core)

    # Sign → proofs (list of Base58 strings)
    proof = sign_order_proof(order_core)
    order_core["proofs"] = [proof]

    # Whitelist for final payload
    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    # Final guard and debug
    ensure_no_matcher_pk(final_payload)
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
