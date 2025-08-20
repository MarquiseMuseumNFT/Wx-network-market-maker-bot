import asyncio
from playwright.async_api import async_playwright

class WXExchange:
    def __init__(self, settings):
        self.settings = settings
        self.base_url = getattr(settings, "wx_url", "https://wx.network")
        self.amount_asset = settings.amount_asset_id
        self.price_asset = settings.price_asset_id

        self.playwright = None
        self.browser = None
        self.page = None

    async def connect(self):
        print("🔌 Connecting to WX (Chromium)...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--no-sandbox"]
        )
        self.page = await self.browser.new_page()

        # Navigate directly to the spot trading pair
        pair_url = f"{self.base_url}/trading/spot/{self.amount_asset}_{self.price_asset}"
        await self.page.goto(pair_url)
        await self.page.wait_for_load_state("networkidle")
        print(f"✅ WX frontend loaded at {pair_url}")

    async def list_open_orders(self):
        print("📋 Fetching open orders from DOM...")
        try:
            rows = await self.page.query_selector_all("div.open-orders-table tr")
            orders = []
            for row in rows:
                text = await row.inner_text()
                parts = text.split()
                if len(parts) >= 3:
                    side, price, amount = parts[0], parts[1], parts[2]
                    orders.append({
                        "side": side.lower(),
                        "price": float(price),
                        "amount": float(amount),
                        "id": "_".join(parts)  # crude unique ID
                    })
            return orders
        except Exception as e:
            print("⚠️ Failed to parse open orders:", e)
            return []

    async def place_orders(self, orders):
        print(f"📝 Placing {len(orders)} orders...")
        for o in orders:
            try:
                if o["side"] == "buy":
                    await self.page.click("button:has-text('Buy')")
                else:
                    await self.page.click("button:has-text('Sell')")

                await self.page.fill("input[name=price]", str(o["price"]))
                await self.page.fill("input[name=amount]", str(o["amount"]))
                await self.page.click("button:has-text('Place Order')")
                await asyncio.sleep(0.5)
                print(f"✅ Placed {o['side']} {o['amount']} @ {o['price']}")
            except Exception as e:
                print(f"❌ Failed to place order {o}: {e}")

    async def cancel_orders(self, order_ids):
        print(f"❌ Cancelling {len(order_ids)} orders...")
        for oid in order_ids:
            try:
                selector = f"text={oid} >> .. >> button:has-text('Cancel')"
                btn = await self.page.query_selector(selector)
                if btn:
                    await btn.click()
                    print(f"✅ Cancelled order {oid}")
                    await asyncio.sleep(0.3)
            except Exception as e:
                print(f"⚠️ Failed to cancel {oid}: {e}")

    async def cancel_all(self):
        print("⚠️ Cancelling ALL open orders...")
        try:
            cancel_buttons = await self.page.query_selector_all("button:has-text('Cancel')")
            for btn in cancel_buttons:
                await btn.click()
                await asyncio.sleep(0.2)
            print("✅ All orders cancelled")
        except Exception as e:
            print("⚠️ Failed cancel_all:", e)

    async def close(self):
        print("🔒 Closing WX session...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# local test
if __name__ == "__main__":
    async def main():
        class DummySettings:
            amount_asset_id = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
            price_asset_id = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"
            wx_url = "https://wx.network"

        wx = WXExchange(DummySettings)
        await wx.connect()
        orders = [
            {"side": "buy", "price": 0.5, "amount": 10},
            {"side": "sell", "price": 1.2, "amount": 5},
        ]
        await wx.place_orders(orders)
        await wx.close()

    asyncio.run(main())
