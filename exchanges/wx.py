import asyncio
import logging
from playwright.async_api import async_playwright

log = logging.getLogger("WXExchange")


class WXExchange:
    def __init__(self, target_asset_id: str):
        self.target_asset_id = target_asset_id
        self.browser = None
        self.page = None

    async def connect(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.firefox.launch(headless=False)  # set True on server
        self.page = await self.browser.new_page()

        # Go to WX trading page (pair link directly)
        url = f"https://wx.network/trading/spot/{self.target_asset_id}"
        await self.page.goto(url)
        await asyncio.sleep(5)
        log.info("Connected to WX frontend via Playwright.")

    async def close(self):
        if self.browser:
            await self.browser.close()

    async def list_open_orders(self):
        """Scrape all currently open orders from UI."""
        orders = []
        try:
            await self.page.click("text=Opened")
            await asyncio.sleep(1)

            rows = await self.page.query_selector_all("div:has-text('Price') >> xpath=..//following-sibling::div")
            for row in rows:
                txt = await row.inner_text()
                # crude parse: expect "Price ... Amount ..." in row text
                parts = txt.split()
                if len(parts) >= 2:
                    try:
                        price = float(parts[0])
                        amount = float(parts[1])
                        orders.append({"price": price, "amount": amount})
                    except:
                        continue
        except Exception as e:
            log.error(f"list_open_orders failed: {e}")
        return orders

    async def cancel_orders(self, orders):
        """Cancel specific orders by clicking Cancel in UI."""
        try:
            await self.page.click("text=Opened")
            await asyncio.sleep(0.5)
            rows = await self.page.query_selector_all("div:has-text('Price') >> xpath=..//following-sibling::div")

            for row in rows:
                txt = await row.inner_text()
                for o in orders:
                    if str(o["price"]) in txt and str(o["amount"]) in txt:
                        cancel_btn = await row.query_selector("button:has-text('Cancel')")
                        if cancel_btn:
                            await cancel_btn.click()
                            log.info(f"Cancelled order {o}")
                            await asyncio.sleep(0.3)
        except Exception as e:
            log.error(f"cancel_orders failed: {e}")

    async def place_orders(self, creates):
        """Place buy/sell orders by filling form and clicking button."""
        try:
            for o in creates:
                side = "buy" if o["side"].lower() == "buy" else "sell"

                # Fill Price field
                await self.page.fill("input[placeholder='Price']", str(o["price"]))
                await asyncio.sleep(0.2)

                # Fill Amount field
                await self.page.fill("input[placeholder='Amount']", str(o["amount"]))
                await asyncio.sleep(0.2)

                # Click Buy or Sell button
                if side == "buy":
                    await self.page.click("button:has-text('Buy')")
                else:
                    await self.page.click("button:has-text('Sell')")

                log.info(f"Placed {side.upper()} order {o}")
                await asyncio.sleep(1)  # pause for UI update
        except Exception as e:
            log.error(f"place_orders failed: {e}")

    async def cancel_all(self):
        """Cancel all visible orders in UI."""
        try:
            await self.page.click("text=Opened")
            await asyncio.sleep(1)
            buttons = await self.page.query_selector_all("button:has-text('Cancel')")
            for btn in buttons:
                await btn.click()
                await asyncio.sleep(0.3)
            log.info("Cancelled all orders.")
        except Exception as e:
            log.error(f"cancel_all failed: {e}")
