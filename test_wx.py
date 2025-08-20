import asyncio
from playwright.async_api import async_playwright
from wx_exchange import WXExchange
from grid import Order

# Replace with your token IDs
AMOUNT_ASSET_ID = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"  # amount token
PRICE_ASSET_ID = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"  # price token (e.g. USDT)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # set True on render
        page = await browser.new_page()

        wx = WXExchange(page, amount_asset_id=AMOUNT_ASSET_ID, price_asset_id=PRICE_ASSET_ID)

        # 1. Cancel all old orders
        await wx.cancel_all()

        # 2. Check existing
        open_orders = await wx.list_open_orders()
        print("📊 Open orders:", open_orders)

        # 3. Place sample grid
        test_orders = [
            Order(id=None, side="buy", price=0.1, size=5),
            Order(id=None, side="sell", price=0.2, size=5)
        ]
        await wx.place_orders(test_orders)

        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
