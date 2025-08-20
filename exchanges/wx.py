import asyncio
from playwright.async_api import async_playwright

class WXExchange:
    def __init__(self, settings):
        self.settings = settings
        self.base_url = "https://wx.network/trading/spot"
        self.playwright = None
        self.browser = None
        self.page = None

    async def connect(self):
        print("🔌 Connecting to WX (Chromium)...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

        url = f"{self.base_url}/{self.settings.AMOUNT_ASSET_ID}_{self.settings.PRICE_ASSET_ID}"
        await self.page.goto(url)
        await self.page.wait_for_selector("text=Order Book")  # sanity check
        print("✅ WX frontend loaded and trading pair ready.")

    async def list_open_orders(self):
        print("📋 Fetching open orders...")
        orders = []
        # Example: DOM selectors must match WX’s UI
        rows = await self.page.query_selector_all("css=[data-testid='open-order-row']")
        for r in rows:
            oid = await r.get_attribute("data-order-id")
            side = await r.query_selector("css=.side")
            side_text = (await side.inner_text()).lower()
            price = float(await (await r.query_selector(".price")).inner_text())
            amount = float(await (await r.query_selector(".amount")).inner_text())
            orders.append({
                "id": oid,
                "side": side_text,
                "price": price,
                "amount": amount
            })
        return orders

    async def place_orders(self, orders):
        print(f"📝 Placing {len(orders)} orders...")
        for o in orders:
            # Click Buy/Sell tab
            if o["side"] == "buy":
                await self.page.click("text=Buy")
            else:
                await self.page.click("text=Sell")

            # Fill price + amount
            await self.page.fill("input[name=price]", str(o["price"]))
            await self.page.fill("input[name=amount]", str(o["amount"]))

            # Submit
            await self.page.click("button[type=submit]")
            await asyncio.sleep(0.5)  # avoid rate limiting
            print(f"✅ Placed {o['side']} {o['amount']} @ {o['price']}")

    async def cancel_orders(self, order_ids):
        print(f"❌ Cancelling {len(order_ids)} orders...")
        for oid in order_ids:
            cancel_btn = await self.page.query_selector(f"button[data-cancel-order-id='{oid}']")
            if cancel_btn:
                await cancel_btn.click()
                print(f"✅ Cancelled order {oid}")
            await asyncio.sleep(0.3)

    async def cancel_all(self):
        print("⚠️ Cancelling ALL orders...")
        btns = await self.page.query_selector_all("button[data-testid='cancel-order']")
        for b in btns:
            await b.click()
            await asyncio.sleep(0.2)
        print("✅ All orders cancelled.")

    async def close(self):
        print("🔒 Closing WX session...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
