import asyncio
import logging
from playwright.async_api import async_playwright

log = logging.getLogger("WX")

class WXExchange:
    def __init__(self, target_asset_id):
        self.target_asset_id = target_asset_id
        self.browser = None
        self.page = None

    async def connect(self):
        log.info("Starting Playwright browser for WX frontend...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

        # Go to WX sign-in
        await self.page.goto("https://wx.network/sign-in/")

        # Click Software login
        await self.page.click("text=Software")

        # ⚠️ TODO: securely load your SEED/KEY from settings
        await self.page.fill("textarea", "YOUR_SEED_OR_KEY")
        await self.page.click("text=Log In")

        log.info("Logged into WX frontend.")

    async def list_open_orders(self):
        # Example: scrape DOM for order table
        try:
            await self.page.goto("https://wx.network/trading")
            rows = await self.page.query_selector_all("div.order-row")  # adjust selector
            orders = []
            for r in rows:
                txt = await r.inner_text()
                orders.append({"info": txt})
            return orders
        except Exception as e:
            log.error(f"list_open_orders error: {e}")
            return []

    async def place_orders(self, creates):
        for o in creates:
            try:
                log.info(f"Placing order {o.side} {o.size} @ {o.price}")
                await self.page.fill("input[placeholder='Price']", str(o.price))
                await self.page.fill("input[placeholder='Amount']", str(o.size))
                if o.side == "buy":
                    await self.page.click("text=Buy")
                else:
                    await self.page.click("text=Sell")
                await asyncio.sleep(0.5)
            except Exception as e:
                log.error(f"Place order failed: {e}")

    async def cancel_orders(self, cancels):
        for c in cancels:
            try:
                # Click cancel button for each order
                btn = await self.page.query_selector(f"text={c.id}")
                if btn:
                    await btn.click()
                    log.info(f"Cancelled {c.id}")
                    await asyncio.sleep(0.5)
            except Exception as e:
                log.error(f"Cancel failed: {e}")

    async def cancel_all(self):
        try:
            cancel_btns = await self.page.query_selector_all("text=Cancel")
            for b in cancel_btns:
                await b.click()
                await asyncio.sleep(0.3)
        except Exception as e:
            log.error(f"Cancel_all failed: {e}")

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
