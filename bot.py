import os, time, json, base58, hashlib, requests
import ed25519

# --- Config from Render ---
SEED       = os.environ["WAVES_SEED"].encode()
NODE       = os.environ.get("WAVES_NODE", "https://nodes.wavesnodes.com")
MATCHER    = os.environ.get("WX_MATCHER", "https://matcher.wx.network")

GRID_LEVELS     = int(os.environ.get("GRID_LEVELS", 6))
GRID_SPACING_PCT= float(os.environ.get("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL  = float(os.environ.get("ORDER_NOTIONAL", 25))
REFRESH_SEC     = int(os.environ.get("REFRESH_SEC", 20))
DRY_RUN         = os.environ.get("DRY_RUN", "true").lower() == "true"

ASSET1 = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
ASSET2 = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

# --- Keys ---
seed_hash = hashlib.blake2b(SEED, digest_size=32).digest()
sk = ed25519.SigningKey(seed_hash)
pk = sk.get_verifying_key()
PUBKEY = base58.b58encode(pk.to_bytes()).decode()

def matcher_key():
    r = requests.get(f"{MATCHER}/matcher")
    r.raise_for_status()
    return r.text.strip()

def get_orderbook():
    url = f"{MATCHER}/matcher/orderbook/{ASSET1}/{ASSET2}"
    return requests.get(url).json()

def sign_order(order: dict) -> dict:
    raw = json.dumps(order, separators=(",", ":"), ensure_ascii=False).encode()
    sig = sk.sign(hashlib.blake2b(raw, digest_size=32).digest())
    order["signature"] = base58.b58encode(sig).decode()
    return order

def place_order(amount, price, side):
    order = {
        "senderPublicKey": PUBKEY,
        "matcherPublicKey": matcher_key(),
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
            ob = get_orderbook()
            mid = (float(ob["bids"][0]["price"]) + float(ob["asks"][0]["price"])) / 2 / 1e8
            for i in range(1, GRID_LEVELS+1):
                delta = mid * (GRID_SPACING_PCT/100) * i
                place_order(ORDER_NOTIONAL, mid - delta, "buy")
                place_order(ORDER_NOTIONAL, mid + delta, "sell")
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run()
