import os
import time
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
WAVES_SEED = os.getenv("WAVES_SEED")
WX_MATCHER = os.getenv("WX_MATCHER", "https://matcher.wx.network")
WAVES_NODE = os.getenv("WAVES_NODE", "https://nodes.wavesnodes.com")

PAIR_BASE = os.getenv("PAIR_BASE")
PAIR_QUOTE = os.getenv("PAIR_QUOTE")

GRID_LEVELS = int(os.getenv("GRID_LEVELS", 6))
GRID_SPACING_PCT = float(os.getenv("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL = float(os.getenv("ORDER_NOTIONAL", 25))
REFRESH_SEC = int(os.getenv("REFRESH_SEC", 20))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
ORDER_TAG = os.getenv("ORDER_TAG", "wx-grid-bot")

# --- Helpers ---
def get_orderbook():
    url = f"{WX_MATCHER}/api/v1/orderbook/{PAIR_BASE}/{PAIR_QUOTE}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

def place_order(price, amount, side):
    if DRY_RUN:
        print(f"[DRYRUN] {side} {amount} @ {price}")
        return
    # 🔒 Here you would sign with your WAVES_SEED (using libsodium)
    # Example payload (unsigned for now):
    payload = {
        "amount": int(amount * 10**8),  # depends on decimals
        "price": int(price * 10**8),
        "orderType": side,
        "matcherPublicKey": "TODO",
        "senderPublicKey": "TODO",
        "matcherFee": 300000,
        "version": 3,
    }
    print("Placing order:", payload)

def run_grid_bot():
    print("🚀 Starting WX Grid Bot")
    while True:
        try:
            ob = get_orderbook()
            best_bid = float(ob["bids"][0]["price"]) if ob["bids"] else 0
            best_ask = float(ob["asks"][0]["price"]) if ob["asks"] else 0
            if not best_bid or not best_ask:
                print("⚠️ No liquidity yet.")
                time.sleep(REFRESH_SEC)
                continue

            mid = (best_bid + best_ask) / 2
            print(f"📊 Mid price: {mid}")

            # Place grid
            for i in range(1, GRID_LEVELS + 1):
                buy_price = mid * (1 - GRID_SPACING_PCT/100 * i)
                sell_price = mid * (1 + GRID_SPACING_PCT/100 * i)
                amount = ORDER_NOTIONAL / mid

                place_order(buy_price, amount, "buy")
                place_order(sell_price, amount, "sell")

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(REFRESH_SEC)

if __name__ == "__main__":
    run_grid_bot()
