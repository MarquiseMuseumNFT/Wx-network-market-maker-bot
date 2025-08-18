import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# --- Config from Render ---
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS     = int(os.environ.get("GRID_LEVELS", 10))   # 10 levels each side
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

def sign_order(order: dict) -> dict:
    # safeguard → ensure matcherPublicKey is not included
    order.pop("matcherPublicKey", None)
    raw = json.dumps(order, separators=(",", ":"), ensure_ascii=False).encode()
    sig = sk.sign(hashlib.blake2b(raw, digest_size=32).digest()).signature
    order["signature"] = base58.b58encode(sig).decode()
    return order

def place_order(amount, price, side):
    order = {
        "senderPublicKey": PUBKEY,
        "amount": int(amount * 10**8),   # assumes 8 decimals
        "price": int(price * 10**8),
        "orderType": side,
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
    r = requests.post(f"{MATCHER}/matcher/orderbook", json=signed)
    print("Order resp:", r.text)

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
