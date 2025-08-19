import asyncio
import logging
import os
from playwright.async_api import async_playwright

log = logging.getLogger("WXExchange")

class WXExchange:
    def __init__(self, target_asset_id: str):
        self.target_asset_id = target_asset_id
        self.playwright = None
        self.browser = None
        self.page = None

    async def connect(self):
        log.info("Launching Playwright (headless Firefox)...")

        # Make sure Playwright uses the Docker image’s preinstalled browsers
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"

        self.playwright = await async_playwright().start()

        # Debugging info
        browsers_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
        log.info(f"PLAYWRIGHT_BROWSERS_PATH = {browsers_path}")

        try:
            self.browser = await self.playwright.firefox.launch(headless=True)
            log.info("✅ Firefox launched successfully")
        except Exception as e:
            log.error(f"❌ Failed to launch Firefox: {e}")
            raise

        self.page = await self.browser.new_page()

        # Navigate to WX login
        await self.page.goto("https://wx.network/sign-in", wait_until="networkidle")
        log.info("WX sign-in page loaded.")

        # Grab credentials from environment
        wallet = os.getenv("WX_WALLET")
        password = os.getenv("WX_LOGIN_PASS")

        if not wallet or not password:
            raise RuntimeError("Missing WX_WALLET or WX_LOGIN_PASS in environment variables")

        # Fill login form
        await self.page.fill("input[type='text']", wallet)
        await self.page.fill("input[type='password']", password)
        await self.page.click("button[type='submit']")

        # Wait until navigation completes
        await self.page.wait_for_load_state("networkidle")
        log.info("WX login complete.")

    async def list_open_orders(self):
        log.info("Fetching open orders via frontend DOM scrape...")
        orders = await self.page.query_selector_all(".orders-table-row")
        return [await o.inner_text() for o in orders]

    async def place_orders(self, orders):
        log.info(f"Placing {len(orders)} orders (frontend emulation).")
        # TODO: Implement order placement clicks
        return []

    async def cancel_orders(self, order_ids):
        log.info(f"Cancelling {len(order_ids)} orders (frontend emulation).")
        # TODO: Implement cancel click sequence
        return []

    async def cancel_all(self):
        log.info("Cancelling all orders (frontend emulation).")
        # TODO: Implement bulk cancel
        return []

    async def close(self):
        log.info("Closing Playwright browser...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
