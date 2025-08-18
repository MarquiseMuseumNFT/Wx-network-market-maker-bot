import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# =========================
# Config (env overrides OK)
# =========================
SEED        = os.environ["WAVES_SEED"].encode()
NODE        = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER     = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS      = int(os.environ.get("GRID_LEVELS", 10))     # levels each side
GRID_SPACING_PCT = float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL   = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC      = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN          = os.environ.get("DRY_RUN", "false").lower() == "true"

# WX pair (amountAsset / priceAsset)
ASSET1 = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
ASSET2 = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

# ===========
# Key derivs
# ===========
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

# ===============
# Small utilities
# ===============
def now_ms() -> int:
    return int(time.time() * 1000)

def wl(d: dict, allowed: set) -> dict:
    """ Whitelist keys in dict """
    return {k: d[k] for k in allowed if k in d}

def ensure_no_matcher_pk(obj):
    """ Recursively assert we never include 'matcherPublicKey' """
    payload = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    if "matcherPublicKey" in payload:
        raise RuntimeError("matcherPublicKey found in payload; aborting")

# Allowed order keys for WX (v3 trustless-style, NO matcherPublicKey)
ALLOWED_ORDER_KEYS = {
    "senderPublicKey",
    "amount",
    "price",
    "orderType",
    "matcherFee",
    "version",
    "timestamp",
    "expiration",
    "assetPair",
    "proofs",
}

# ==================
# Price feed helpers
# ==================
def get_htx_price():
    url = "https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    # Public orderbook (per pair)
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    ob = r.json()
    # WX returns integer prices in 1e-8 steps
    bid = float(ob["bids"][0]["price"])
    ask = float(ob["asks"][0]["price"])
    return (bid + ask) / 2 / 1e8

def get_price():
    try:
        return get_htx_price()
    except Exception as e:
        print("HTX feed failed, fallback to WX mid →", e)
        return get_wx_mid()

# =========================
# Signatures (proofs array)
# =========================
def blake2b256(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=32).digest()

def sign_order_proof(order_dict: dict) -> str:
    """
    Produce a Base58-encoded proof. This signs a Blake2b-256 hash of the
    exact JSON we send (keys/values identical to payload), which matches
    the 'local signing' pattern many WX integrators use for v3 trustless flow.
    If your matcher later requires strict binary serialization, swap this out.
    """
    # Don't allow accidental matcherPublicKey
    ensure_no_matcher_pk(order_dict)

    # The proof must reflect the exact fields/values being sent.
    # We'll compute after final whitelist & fill-in in place_order().
    raise RuntimeError("sign_order_proof() should be called with the FINAL payload")

# ======================
# Orderbook API wrappers
# ======================
def post_order(payload: dict):
    """
    POST per-pair endpoint to avoid 404 and match WX expectations.
    """
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("Order resp:", r.status_code, r.text)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        # Surface body for debugging
        try:
            body = r.text
        except Exception:
            body = "<no body>"
        print("HTTPError posting order:", e, body)
        raise

def get_my_orders():
    """
    Active orders for a public key (per pair).
    NOTE: Some deployments expect /{address}/active instead of PUBKEY.
    WX docs show PUBKEY; if 404 persists, map PUBKEY->address and use that.
    """
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/{PUBKEY}/active"
    r = requests.get(url, timeout=10)
    if r.status_code == 404:
        # Keep the message visible; caller will handle gracefully.
        raise requests.HTTPError(f"404 on get_my_orders: {url}")
    r.raise_for_status()
    return r.json()

def cancel_order(order_id: str):
    """
    Pair-scoped cancel endpoint. Some deployments accept body with orderId+sender.
    """
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel"
    payload = {"orderId": order_id, "sender": PUBKEY}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return True
    r = requests.post(url, json=payload, timeout=10)
    print("Cancel resp:", r.status_code, r.text)
    r.raise_for_status()
    return True

def cancel_all():
    try:
        orders = get_my_orders()
        for o in orders:
            try:
                cancel_order(o["id"])
            except Exception as ce:
                print("Cancel single order failed:", o.get("id"), ce)
    except Exception as e:
        # This used to spam: "Expecting value: line 1 column 1 (char 0)" when empty/HTML
        print("Cancel error:", e)

# =====================
# Order construction v3
# =====================
def place_order(amount_units: float, price_quote: float, side: str):
    """
    Build a v3 order WITHOUT matcherPublicKey, sign locally into proofs[], and send.
    amount_units: base units (amount asset) in float; scaled to 1e8
    price_quote:  quote price; scaled to 1e8 per WX format
    side: "buy" or "sell"
    """
    # Core (before signing)
    order_core = {
        "senderPublicKey": PUBKEY,  # REQUIRED
        "amount": int(round(amount_units * 10**8)),
        "price": int(round(price_quote * 10**8)),
        "orderType": side,  # "buy" or "sell"
        "matcherFee": 300000,
        "version": 3,
        "timestamp": now_ms(),
        "expiration": now_ms() + 24 * 60 * 60 * 1000,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
    }

    # Paranoid: never allow matcherPublicKey
    if "matcherPublicKey" in order_core:
        del order_core["matcherPublicKey"]
    ensure_no_matcher_pk(order_core)

    # Whitelist BEFORE signing so we sign exactly what we send
    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    # Now produce proof over EXACT json bytes we will POST
    raw = json.dumps(final_payload, separators=(",", ":"), ensure_ascii=False).encode()
    digest = blake2b256(raw)
    sig = sk.sign(digest).signature
    proof_b58 = base58.b58encode(sig).decode()

    # Attach proofs
    final_payload["proofs"] = [proof_b58]

    # Final safety
    ensure_no_matcher_pk(final_payload)
    print("Sending keys:", sorted(final_payload.keys()))

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_quote}")
        return True

    return post_order(final_payload)

# ==========
# Main loop
# ==========
def run():
    while True:
        try:
            cancel_all()
            mid = get_price()
            print(f"Mid price used: {mid}")
            for i in range(1, GRID_LEVELS + 1):
                delta = mid * (GRID_SPACING_PCT / 100.0) * i
                # place symmetric grid orders
                place_order(ORDER_NOTIONAL, mid - delta, "buy")
                place_order(ORDER_NOTIONAL, mid + delta, "sell")
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()
