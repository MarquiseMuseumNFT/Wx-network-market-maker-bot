import asyncio
import logging
import os
from playwright.async_api import async_playwright, Error as PlaywrightError

log = logging.getLogger("WXExchange")

class WXExchange:
    def __init__(self, target_asset_id: str, max_retries: int = 3):
        self.target_asset_id = target_asset_id
        self.playwright = None
        self.browser = None
        self.page = None
        self.max_retries = max_retries

    async def connect(self):
        """Connect to WX and log in, retrying if Playwright/browser crashes."""
        retries = 0
        while retries < self.max_retries:
            try:
                log.info("Launching Playwright (headless Firefox)...")
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.firefox.launch(headless=True)
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

                # Wait until navigation completes (success = dashboard/trading page)
                await self.page.wait_for_load_state("networkidle")
                log.info("WX login complete.")
                return  # ✅ success, exit retry loop

            except PlaywrightError as e:
                retries += 1
                log.error(f"Playwright error: {e} (retry {retries}/{self.max_retries})")
                await self.close()
                await asyncio.sleep(5)  # backoff before retry

        raise RuntimeError("Failed to connect to WX after retries.")

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
            try:
                await self.browser.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        self.browser = None
        self.playwright = None
        self.page = None
