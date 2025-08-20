# test_wx.py
import asyncio
from playwright.async_api import async_playwright
from exchanges.wx_exchange import WXExchange
from grid import build_grid, diff_books


async def main():
    url = "https://wx.network/trading/spot/9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # set True if you want background
        page = await browser.new_page()

        # Open trading pair
        await page.goto(url)

        # TODO: if you need login, add code here (e.g., wallet connect)

        # pair asset IDs (USDT/WAVES as example, update if needed)
        asset_id = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"      # WAVES
        price_asset_id = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"  # USDT

        wx = WXExchange(page, asset_id, price_asset_id)

        # Get current orders (from frontend DOM)
        current_orders = await wx.list_open_orders()

        # Build a grid
        mid = 1.0  # TODO: replace with await wx.get_mid_price()
        target_orders = build_grid(mid, levels=3, spacing_bps=50, size=0.1)

        cancels, creates = diff_books(current_orders, target_orders)

        print("Need to cancel:", cancels)
        print("Need to create:", creates)

        # Place and cancel orders
        for oid in cancels:
            await wx.cancel_order(oid)

        for order in creates:
            await wx.place_order(order["side"], order["price"], order["amount"])

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
