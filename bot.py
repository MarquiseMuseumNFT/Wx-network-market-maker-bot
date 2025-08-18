import os, time, json, base58, hashlib, requests
from nacl.signing import SigningKey

# --- Config from Render ---
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS     = int(os.environ.get("GRID_LEVELS", 10))
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

def sign(data: dict) -> dict:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    sig = sk.sign(hashlib.blake2b(raw, digest_size=32).digest()).signature
    data["signature"] = base58.b58encode(sig).decode()
    return data

def get_htx_price():
    r = requests.get("https://api-aws.huobi.pro/market/detail/merged?symbol=wavesusdt", timeout=5)
    r.raise_for_status()
    return float(r.json()["tick"]["close"])

def get_wx_mid():
    r = requests.get(f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}", timeout=5)
    r.raise_for_status()
    ob = r.json()
    return (float(ob["bids"][0]["price"]) + float(ob["asks"][0]["price"])) / 2 / 1e8

def get_price():
    try: return get_htx_price()
    except Exception as e:
        print("HTX feed failed → fallback:", e)
        return get_wx_mid()

def get_my_orders():
    return requests.get(f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/{PUBKEY}/active").json()

def cancel_order(order_id):
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}/cancel"
    payload = {"orderId": order_id, "sender": PUBKEY}
    if DRY_RUN:
        print(f"DRY RUN → Cancel {order_id}")
        return
    signed = sign(payload)
    r = requests.post(url, json=signed)
    print("Cancel resp:", r.text)

def cancel_all():
    try:
        for o in get_my_orders():
            cancel_order(o["id"])
    except Exception as e:
        print("Cancel error:", e)

def place_order(amount, price, side):
    order = {
        "senderPublicKey": PUBKEY,
        "amount": int(amount * 10**8),
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
    signed = sign(order)
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
