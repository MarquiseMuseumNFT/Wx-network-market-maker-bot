import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# --- Config from Render ---
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS      = int(os.environ.get("GRID_LEVELS", 10))   # grid levels each side
GRID_SPACING_PCT = float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL   = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC      = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN          = os.environ.get("DRY_RUN", "false").lower() == "true"

ASSET1 = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
ASSET2 = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

# --- Keys ---
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = SigningKey(seed_hash)
pk = sk.verify_key
PUBKEY = base58.b58encode(pk.encode()).decode()

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

# --- Price feeds ---
def get_htx_price():
    url = "https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt"
    r = SESSION.get(url, timeout=5)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    r = SESSION.get(url, timeout=5)
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

# --- Orders ---
def get_my_orders():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/{PUBKEY}/active"
    r = SESSION.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def cancel_order(order_id):
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel"
    payload = {"orderId": order_id, "sender": PUBKEY}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return
    try:
        r = SESSION.post(url, data=json.dumps(payload), timeout=10)
        # Some matchers respond 200 with JSON; others may send empty body.
        try:
            print("Cancel resp:", r.status_code, r.text or "<empty>")
        except Exception:
            print("Cancel resp:", r.status_code, "<non-text body>")
    except Exception as e:
        print("Cancel error:", e)

def cancel_all():
    try:
        orders = get_my_orders()
        for o in orders:
            cancel_order(o["id"])
    except Exception as e:
        print("Cancel error:", e)

def sign_order(order: dict) -> dict:
    """
    WX matcher must NOT receive 'matcherPublicKey' in the JSON.
    We sign and provide Base58 proof in 'proofs'.
    """
    # Extra hardening: strip any stray field that could cause schema rejection.
    for k in ("matcherPublicKey", "eip712Signature", "proof"):
        if k in order:
            order.pop(k, None)

    # Lightweight signing that matches earlier behaviour (blake2b over compact JSON).
    # If the matcher later complains about signature validity, we can switch to full
    # binary OrderV3 serialization — but schema errors must be fixed first.
    raw_json = json.dumps(order, separators=(",", ":"), ensure_ascii=False).encode()
    digest = hashlib.blake2b(raw_json, digest_size=32).digest()
    sig = sk.sign(digest).signature
    b58sig = base58.b58encode(sig).decode()

    # Use 'proofs' array (preferred) instead of legacy 'signature' field.
    order["proofs"] = [b58sig]
    return order

def place_order(amount, price, side):
    order = {
        "senderPublicKey": PUBKEY,
        "amount": int(amount * 10**8),   # assumes 8 decimals
        "price": int(price * 10**8),
        "orderType": side,               # "buy" | "sell"
        "matcherFee": 300000,
        "version": 3,
        "timestamp": int(time.time() * 1000),
        "expiration": int(time.time() * 1000) + 24*60*60*1000,
        "assetPair": {"amountAsset": ASSET1, "priceAsset": ASSET2},
    }

    if DRY_RUN:
        print(f"DRY RUN → {side} {amount} @ {price}")
        return

    signed = sign_order(order)

    # Sanity log to verify the exact keys we send
    if "matcherPublicKey" in signed:
        print("⚠️ matcherPublicKey present in outgoing JSON — will be rejected.")
    print("Sending keys:", sorted(list(signed.keys())))

    url = f"{MATCHER}/matcher/orderbook"
    r = SESSION.post(url, data=json.dumps(signed), timeout=15)
    print("Order resp:", r.status_code, r.text)

# --- Main loop ---
def run():
    while True:
        try:
            cancel_all()
            mid = get_price()
            print(f"Mid price used: {mid}")
            for i in range(1, GRID_LEVELS + 1):
                delta = mid * (GRID_SPACING_PCT / 100) * i
                place_order(ORDER_NOTIONAL, mid - delta, "buy")
                place_order(ORDER_NOTIONAL, mid + delta, "sell")
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()
