import os
import asyncio
from wx import WXExchange

async def main():
    amount_asset = os.getenv("AMOUNT_ASSET_ID")
    price_asset = os.getenv("PRICE_ASSET_ID")

    if not amount_asset or not price_asset:
        raise ValueError("❌ Missing env vars: AMOUNT_ASSET_ID and PRICE_ASSET_ID must be set.")

    wx = WXExchange(
        amount_asset=amount_asset,
        price_asset=price_asset
    )

    await wx.connect()

    # --- demo calls ---
    open_orders = await wx.list_open_orders()
    print("Open orders:", open_orders)

    await wx.place_orders([
        {"side": "buy", "price": "1.0", "amount": "10"},
        {"side": "sell", "price": "2.0", "amount": "5"}
    ])

    await wx.cancel_orders(["dummy_order_id"])
    await wx.cancel_all()

    await wx.close()

if __name__ == "__main__":
    asyncio.run(main())
