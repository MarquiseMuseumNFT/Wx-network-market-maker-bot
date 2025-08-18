import os
import time
import math
import requests
import pywaves as pw
from dotenv import load_dotenv

# Load .env config
load_dotenv()

SEED = os.getenv("WAVES_SEED")
MATCHER = os.getenv("WX_MATCHER", "https://matcher.wx.network")
NODE = os.getenv("WAVES_NODE", "https://nodes.wavesnodes.com")

GRID_LEVELS = int(os.getenv("GRID_LEVELS", 6))
GRID_SPACING_PCT = float(os.getenv("GRID_SPACING_PCT", 0.35))
ORDER_NOTIONAL = float(os.getenv("ORDER_NOTIONAL", 25))
REFRESH_SEC = int(os.getenv("REFRESH_SEC", 20))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
ORDER_TAG = os.getenv("ORDER_TAG", "wx-grid-bot")

# Pair from WX link
AMOUNT_ASSET_ID = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
PRICE_ASSET_ID = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

pw.setNode(NODE, "mainnet")
pw.setMatcher(MATCHER)
account = pw.Address(seed=SEED)

amount_asset = pw.Asset(AMOUNT_ASSET_ID)
price_asset = pw.Asset(PRICE_ASSET_ID)
pair = pw.AssetPair(amount_asset, price_asset)

def get_orderbook_info():
    url = f"{MATCHER}/matcher/orderbook/{AMOUNT_ASSET_ID}/{PRICE_ASSET_ID}/info"
    return requests.get(url).json()

def get_market_status():
    url = f"{MATCHER}/matcher/orderbook/{AMOUNT_ASSET_ID}/{PRICE_ASSET_ID}/status"
    return requests.get(url).json()

def calculate_fee(order):
    url = f"{MATCHER}/matcher/orderbook/calculateFee"
    r = requests.post(url, json=order)
    return r.json().get("matcherFee", 300000)  # fallback: 0.003 WAVES

def round_step(value, step, side="floor"):
    if step == 0:
        return value
    if side == "floor":
        return math.floor(value / step) * step
    else:
        return math.ceil(value / step) * step

def place_order(side, price, amount):
    raw_order = {
        "matcherPublicKey": requests.get(f"{MATCHER}/matcher").json()["matcherPublicKey"],
        "orderType": side,
        "assetPair": {"amountAsset": AMOUNT_ASSET_ID, "priceAsset": PRICE_ASSET_ID},
        "price": int(price * (10 ** price_asset.decimals)),
        "amount": int(amount * (10 ** amount_asset.decimals)),
        "senderPublicKey": account.publicKey,
    }
    fee = calculate_fee(raw_order)

    if DRY_RUN:
        print(f"[DRY-RUN] {side.upper()} {amount} @ {price} | fee: {fee}")
    else:
        if side == "buy":
            tx = account.buy(pair, amount, price, matcherFee=fee)
        else:
            tx = account.sell(pair, amount, price, matcherFee=fee)
        print("Placed:", tx)

def run_grid():
    ob_info = get_orderbook_info()
    step_price = 10 ** -ob_info["priceAssetDecimals"]
    step_amount = 10 ** -ob_info["amountAssetDecimals"]

    status = get_market_status()
    best_bid = float(status["bids"][0]["price"]) / (10 ** price_asset.decimals) if status["bids"] else 0
    best_ask = float(status["asks"][0]["price"]) / (10 ** price_asset.decimals) if status["asks"] else 0
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else best_bid or best_ask

    print(f"Best bid: {best_bid}, Best ask: {best_ask}, Mid: {mid}")

    for i in range(1, GRID_LEVELS + 1):
        offset = i * (GRID_SPACING_PCT / 100) * mid
        buy_price = round_step(mid - offset, step_price, "floor")
        sell_price = round_step(mid + offset, step_price, "ceil")

        buy_amount = round_step(ORDER_NOTIONAL / buy_price, step_amount)
        sell_amount = round_step(ORDER_NOTIONAL / sell_price, step_amount)

        place_order("buy", buy_price, buy_amount)
        place_order("sell", sell_price, sell_amount)

if __name__ == "__main__":
    while True:
        try:
            run_grid()
        except Exception as e:
            print("Error:", e)
        time.sleep(REFRESH_SEC)
