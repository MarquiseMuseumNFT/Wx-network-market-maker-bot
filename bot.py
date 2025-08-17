import os
import pywaves as pw
import time

# === Load settings from environment variables ===
SEED = os.getenv("SEED")
AMOUNT_ASSET = os.getenv("AMOUNT_ASSET")
PRICE_ASSET = os.getenv("PRICE_ASSET")
ORDER_SIZE = int(os.getenv("ORDER_SIZE", "100"))
SPREAD = float(os.getenv("SPREAD", "0.5")) / 100   # convert percent to fraction
LEVELS = int(os.getenv("LEVELS", "5"))

# === Connect to WX ===
pw.setNode(node="https://nodes.wavesnodes.com", chain="W", matcher="https://matcher.waves.exchange")

my_wallet = pw.Address(seed=SEED)
amount_asset = pw.Asset(AMOUNT_ASSET)
price_asset = pw.Asset(PRICE_ASSET)
pair = pw.AssetPair(amount_asset, price_asset)

print("Bot started with wallet:", my_wallet.address)

def place_grid_orders():
    try:
        ticker = pair.last()
        if not ticker:
            print("No market data available, retrying...")
            return
        price = float(ticker)
        print(f"Market price: {price}")

        # Cancel previous orders
        my_wallet.cancelOpenOrders(pair)

        # Place buy orders
        for i in range(1, LEVELS + 1):
            buy_price = price * (1 - SPREAD * i)
            my_wallet.buy(pair, ORDER_SIZE, buy_price)
            print(f"Placed BUY {ORDER_SIZE} at {buy_price}")

        # Place sell orders
        for i in range(1, LEVELS + 1):
            sell_price = price * (1 + SPREAD * i)
            my_wallet.sell(pair, ORDER_SIZE, sell_price)
            print(f"Placed SELL {ORDER_SIZE} at {sell_price}")

    except Exception as e:
        print("Error placing grid orders:", e)

# === Main loop ===
while True:
    place_grid_orders()
    time.sleep(60)  # refresh every 60s
