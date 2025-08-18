#!/usr/bin/env python3
import os, time, json, base58, hashlib, requests, struct, re
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

# Fee asset
MATCHER_FEE_ASSET_ID = os.environ.get("MATCHER_FEE_ASSET_ID", "WAVES")

# Signature mode: "fast" (blake2b256(orderBytes)) or "raw" (orderBytes directly)
SIGN_MODE = os.environ.get("SIGN_MODE", "fast").lower().strip()  # "fast" | "raw"

# ===============================
# Keys
# ===============================
# Derive signing key from SEED (32-byte seed to ed25519)
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
    return struct.pack(">q", int(x))

def _asset_id_bytes(asset_id: str) -> bytes:
    if asset_id is None or asset_id == "" or asset_id.upper() == "WAVES":
        return b"\x00"
    return b"\x01" + base58.b58decode(asset_id)

def _asset_pair_bytes(amount_asset: str, price_asset: str) -> bytes:
    return _asset_id_bytes(amount_asset) + _asset_id_bytes(price_asset)

def order_v3_bytes(order: dict) -> bytes:
    """
    OrderV3 bytes:
      1  : version (0x03)
      32 : senderPublicKey
      32 : matcherPublicKey
      xx : assetPair (amountAsset, priceAsset) with 0x00 or 0x01+32
       1 : orderType (0=buy,1=sell)
       8 : price (be)
       8 : amount (be)
       8 : timestamp (be)
       8 : expiration (be)
       8 : matcherFee (be)
      xx : matcherFeeAssetId (0x00 or 0x01+32)
    """
    b = bytearray()
    b += b"\x03"
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

def sign_bytes(message: bytes, mode: str) -> bytes:
    """
    mode 'fast': sign blake2b256(message)
    mode 'raw' : sign message directly
    """
    if mode == "fast":
        payload = blake2b256(message)
    elif mode == "raw":
        payload = message
    else:
        raise ValueError("SIGN_MODE must be 'fast' or 'raw'")
    return sk.sign(payload).signature

def make_proofs(order: dict, mode: str) -> list[str]:
    msg = order_v3_bytes(order)
    sig = sign_bytes(msg, mode)
    return [base58.b58encode(sig).decode()]

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

INVALID_SIG_CODE = 9440512
INVALID_SIG_RX = re.compile(r'"error"\s*:\s*%d' % INVALID_SIG_CODE)

def post_order(payload: dict):
    url = f"{MATCHER}/matcher/orderbook"
    r = requests.post(url, json=payload, timeout=20)
    ct = r.headers.get("Content-Type","")
    print(f"Order resp: {r.status_code} {r.text}")
    if r.ok and ct.startswith("application/json"):
        return r.json()
    return r.text

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
    # NOTE: do not divide by 1e8 if you plan to submit price longs directly.
    # We'll compute longs explicitly in place_order().
    return (bid + ask) / 2.0

def get_price_long():
    """
    Returns a matcher-scaled price long (not human float).
    Uses WX mid directly so decimals/scaling stay correct.
    """
    try:
        return int(round(get_wx_mid()))
    except Exception as e:
        print("WX mid feed failed, fallback to HTX float →", e)
        # Fallback path (rough): multiply by 1e8 assuming equal decimals
        px = get_htx_price()
        return int(round(px * 1e8))

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
# Place order (auto-retry signing mode)
# ===============================
def place_order(amount_units: float, price_quote_float: float | None, side: str):
    """
    If price_quote_float is None, we use WX mid (as long).
    Otherwise we convert provided float -> matcher price long (roughly 1e8 multiplier).
    """
    if price_quote_float is None:
        price_long = get_price_long()
    else:
        # Only use this path if you *know* decimals; otherwise prefer get_price_long()
        price_long = int(round(price_quote_float * 10**8))

    order_core = {
        "version": 3,
        "senderPublicKey": PUBKEY,
        "matcherPublicKey": MATCHER_PUBKEY,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
        "orderType": side,                      # "buy" or "sell"
        "price": price_long,                    # LONG in matcher scale
        "amount": int(round(amount_units * 10**8)),  # amount in AMOUNT_ASSET minimal units (assumes 8 decimals)
        "timestamp": now_ms(),
        "expiration": now_ms() + 24 * 60 * 60 * 1000,
        "matcherFee": 1000000,                  # 0.01 WAVES
        "matcherFeeAssetId": MATCHER_FEE_ASSET_ID,
    }

    # First attempt with configured SIGN_MODE
    order_core["proofs"] = make_proofs(order_core, SIGN_MODE)
    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    print("Sending keys:", sorted(final_payload.keys()))
    print("Final payload before sending:", final_payload)

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_long} (long)")
        return True

    resp = requests.post(f"{MATCHER}/matcher/orderbook", json=final_payload, timeout=20)
    print(f"Order resp: {resp.status_code} {resp.text}")

    # If invalid signature, auto-retry with the other signing mode
    if (resp.status_code == 400) and INVALID_SIG_RX.search(resp.text or ""):
        alt_mode = "raw" if SIGN_MODE == "fast" else "fast"
        print(f"Retrying with SIGN_MODE='{alt_mode}'")
        order_core["proofs"] = make_proofs(order_core, alt_mode)
        final_payload = wl(order_core, ALLOWED_ORDER_KEYS)
        resp = requests.post(f"{MATCHER}/matcher/orderbook", json=final_payload, timeout=20)
        print(f"Order resp (retry): {resp.status_code} {resp.text}")

    # Return JSON if available
    ct = resp.headers.get("Content-Type","")
    if resp.ok and ct.startswith("application/json"):
        return resp.json()
    return resp.text

# ===============================
# Strategy loop
# ===============================
def run():
    while True:
        try:
            cancel_all()
            # Use WX mid in matcher long scale so price decimals are correct
            mid_long = get_price_long()
            print(f"Mid (long) used: {mid_long}")

            # Compute step as % of human price -> translate to long.
            # We'll convert mid_long back to human float only to compute percentage steps.
            # NOTE: this assumes 1e8 scale; if your pair has different decimals diff,
            # the mid_long already includes it, but we can't infer human value.
            # So we apply the percentage on the long directly.
            step_long = int(round(mid_long * (GRID_SPACING_PCT / 100.0)))

            for i in range(1, GRID_LEVELS + 1):
                p_buy_long  = max(1, mid_long - i * step_long)
                p_sell_long = max(1, mid_long + i * step_long)
                place_order(ORDER_NOTIONAL, None, "buy")   # use WX mid internally for each call
                place_order(ORDER_NOTIONAL, None, "sell")  # ditto
                # If you want symmetric around the captured mid, pass explicit longs:
                # place_order(ORDER_NOTIONAL, p_buy_long / 1e8, "buy")
                # place_order(ORDER_NOTIONAL, p_sell_long / 1e8, "sell")

        except Exception as e:
            print("Error in main loop:", repr(e))

        time.sleep(REFRESH_SEC)

# ===============================
# Entry
# ===============================
if __name__ == "__main__":
    run()
