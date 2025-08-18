import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# ---------- Config ----------
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS      = int(os.environ.get("GRID_LEVELS", 10))     # levels each side
GRID_SPACING_PCT = float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL   = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC      = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN          = os.environ.get("DRY_RUN", "false").lower() == "true"

ASSET1 = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
ASSET2 = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

SESSION = requests.Session()
SESSION.headers.update({
    "Content-Type": "application/json; charset=utf-8",
    "Accept": "application/json",
    "User-Agent": "wx-grid-bot/1.0"
})

# ---------- Keys ----------
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

# ---------- Utilities ----------
def log_http_error(prefix: str, resp: requests.Response):
    try:
        text = resp.text
    except Exception:
        text = "<no text>"
    print(f"{prefix}: {resp.status_code} {text}")

def ensure_no_matcher_pk(obj: dict):
    # hard guard: never allow this key, anywhere
    if "matcherPublicKey" in obj:
        raise ValueError("matcherPublicKey must not be present")
    # scan JSON string just in case something odd slipped in via aliasing
    s = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    if "matcherPublicKey" in s:
        raise ValueError("Serialized payload accidentally contains matcherPublicKey")

def wl(d: dict, allowed: set) -> dict:
    return {k: v for k, v in d.items() if k in allowed}

def now_ms() -> int:
    return int(time.time() * 1000)

# ---------- Price feeds ----------
def get_htx_price():
    url = "https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt"
    r = SESSION.get(url, timeout=5)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    r = SESSION.get(url, timeout=7)
    r.raise_for_status()
    ob = r.json()
    bid = float(ob["bids"][0]["price"])
    ask = float(ob["asks"][0]["price"])
    # on WX orderbook, prices are often in 1e8 price steps
    return (bid + ask) / 2 / 1e8

def get_price():
    try:
        return get_htx_price()
    except Exception as e:
        print("HTX feed failed, fallback to WX mid →", e)
        return get_wx_mid()

# ---------- Orders API helpers ----------
def get_my_orders():
    # Try new-ish path first, then legacy
    paths = [
        f"{MATCHER}/api/v1/orderbook/{ASSET1}/{ASSET2}/publicKey/{PUBKEY}/active",
        f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/{PUBKEY}/active",
    ]
    for url in paths:
        try:
            r = SESSION.get(url, timeout=8)
            if r.status_code == 200:
                return r.json()
            if r.status_code != 404:
                log_http_error("Active orders error", r)
        except Exception as e:
            print("Active orders exception:", e)
    return []

def cancel_order(order_id):
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return

    bodies = [
        {"orderId": order_id, "sender": PUBKEY},
        {"orderId": order_id},  # some deployments ignore 'sender'
    ]
    paths = [
        f"{MATCHER}/api/v1/orderbook/{ASSET1}/{ASSET2}/cancel",
        f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel",
    ]

    for url in paths:
        for payload in bodies:
            try:
                r = SESSION.post(url, data=json.dumps(payload), timeout=8)
                if r.status_code in (200, 202):
                    print("Cancel ok:", r.text)
                    return
                # 404 might mean wrong endpoint; try next
                if r.status_code not in (404, 405):
                    log_http_error("Cancel resp", r)
            except Exception as e:
                print("Cancel exception:", e)

def cancel_all():
    try:
        orders = get_my_orders()
        for o in orders:
            oid = o.get("id") or o.get("orderId") or o.get("orderID")
            if oid:
                cancel_order(oid)
    except Exception as e:
        print("Cancel error:", e)

# ---------- Signing ----------
def sign_order_proof(order_obj: dict) -> str:
    """
    WX expects Base58 proofs. We’ll sign a blake2b hash of the compact JSON.
    This matches the simplified approach you used and is acceptable for our purposes here.
    """
    raw = json.dumps(order_obj, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.blake2b(raw, digest_size=32).digest()
    sig = sk.sign(digest).signature
    return base58.b58encode(sig).decode()

# ---------- Place order ----------
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

def post_order(payload: dict):
    # Try modern then legacy endpoint
    urls = [
        f"{MATCHER}/api/v1/orderbook",
        f"{MATCHER}/matcher/orderbook",
    ]
    for url in urls:
        try:
            resp = SESSION.post(url, data=json.dumps(payload), timeout=10)
            if resp.status_code in (200, 202):
                print("Order resp:", resp.text)
                return True
            log_http_error("Order resp", resp)
        except Exception as e:
            print("Order exception:", e)
    return False

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

    # Strictly forbid matcherPublicKey
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
    payload_str = json.dumps(final_payload, separators=(",", ":"), ensure_ascii=False)
    if "matcherPublicKey" in payload_str:
        raise RuntimeError("matcherPublicKey appeared in serialized payload unexpectedly")

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount_units} @ {price_quote}")
        return True

    return post_order(final_payload)

# ---------- Main loop ----------
def run():
    while True:
        try:
            cancel_all()

            mid = get_price()
            print(f"Mid price used: {mid}")

            for i in range(1, GRID_LEVELS + 1):
                delta = mid * (GRID_SPACING_PCT / 100.0) * i
                # place buy
                place_order(ORDER_NOTIONAL, max(0.00000001, mid - delta), "buy")
                # place sell
                place_order(ORDER_NOTIONAL, mid + delta, "sell")

        except Exception as e:
            print("Error:", e)

        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()
