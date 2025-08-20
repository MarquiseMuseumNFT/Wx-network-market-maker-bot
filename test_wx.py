# test_wx.py
import asyncio
from playwright.async_api import async_playwright
from exchanges.wx_exchange import WXExchange
from grid import build_grid, diff_books

async def main():
    url = "https://wx.network/trading/spot/9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # set True for background
        page = await browser.new_page()

        wx = WXExchange(
            page,
            asset_id="9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX",
            price_asset_id="EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"
        )

        await wx.goto_market()

        # Get current grid state
        current_orders = await wx.list_open_orders()
        mid = await wx.get_mid_price()

        # Build new grid
        target_orders = build_grid(mid, levels=3, spacing_bps=50, size=0.1)
        cancels, creates = diff_books(current_orders, target_orders)

        print("Need to cancel:", cancels)
        print("Need to create:", creates)

        # Cancel
        for oid in cancels:
            await wx.cancel_order(oid)

        # Create
        for order in creates:
            await wx.place_order(order["side"], order["price"], order["amount"])

        await asyncio.sleep(10)  # keep browser open for inspection
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
