import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# --- Config from Render ---
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS     = int(os.environ.get("GRID_LEVELS", 10))   # grid levels each side
GRID_SPACING_PCT= float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL  = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC     = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN         = os.environ.get("DRY_RUN", "false").lower() == "true"

ASSET1 = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
ASSET2 = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

# --- Keys ---
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

# --- Allowed order keys ---
ALLOWED_ORDER_KEYS = {
    "senderPublicKey", "amount", "price", "orderType", "matcherFee",
    "version", "timestamp", "expiration", "assetPair", "proofs"
}

# --- Helpers ---
def now_ms():
    return int(time.time() * 1000)

def ensure_no_matcher_pk(obj):
    """Sanity check: no matcherPublicKey allowed anywhere"""
    s = json.dumps(obj, separators=(",", ":"))
    if "matcherPublicKey" in s:
        raise RuntimeError("matcherPublicKey leaked into payload!")

def wl(d: dict, allowed: set):
    """Whitelist dict keys"""
    return {k: v for k, v in d.items() if k in allowed}

def sign_order_proof(order_core: dict) -> str:
    raw = json.dumps(order_core, separators=(",", ":"), ensure_ascii=False).encode()
    h = hashlib.blake2b(raw, digest_size=32).digest()
    sig = sk.sign(h).signature
    return base58.b58encode(sig).decode()

def post_order(payload: dict):
    url = f"{MATCHER}/matcher/orderbook"
    r = requests.post(url, json=payload, timeout=10)
    print("Order resp:", r.text)
    return r.json()

# --- Orders ---
def get_my_orders():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/{PUBKEY}/active"
    return requests.get(url).json()

def cancel_order(order_id):
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel"
    payload = {"orderId": order_id, "sender": PUBKEY}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return
    r = requests.post(url, json=payload)
    print("Cancel resp:", r.text)

def cancel_all():
    try:
        orders = get_my_orders()
        for o in orders:
            cancel_order(o["id"])
    except Exception as e:
        print("Cancel error:", e)

def place_order(amount_units: float, price_quote: float, side: str):
    # Amount and price scaling (assumes 8 decimals for both assets/pair)
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

    # Strictly forbid matcherPublicKey and senderPublicKey rewriting
    if "matcherPublicKey" in order_core:
        del order_core["matcherPublicKey"]

    ensure_no_matcher_pk(order_core)

    # Sign -> proofs (list of Base58 strings)
    proof = sign_order_proof(order_core)
    order_core["proofs"] = [proof]

    # Final whitelist
    final_payload = wl(order_core, ALLOWED_ORDER_KEYS)

    # Final sanity check & debug
    ensure_no_matcher_pk(final_payload)
    print("Sending keys:", sorted(final_payload.keys()))

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_quote}")
        return True

    return post_order(final_payload)

# --- Price feeds ---
def get_htx_price():
    url = "https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    r = requests.get(url, timeout=5)
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

# --- Main loop ---
def run():
    while True:
        try:
            cancel_all()
            mid = get_price()
            print(f"Mid price used: {mid}")
            for i in range(1, GRID_LEVELS+1):
                delta = mid * (GRID_SPACING_PCT/100) * i
                place_order(ORDER_NOTIONAL, mid - delta, "buy")
                place_order(ORDER_NOTIONAL, mid + delta, "sell")
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()

