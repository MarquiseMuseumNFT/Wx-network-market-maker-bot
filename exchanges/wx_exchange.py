import asyncio
from playwright.async_api import async_playwright

class WXExchange:
    def __init__(self, page, asset_id, price_asset_id, base_url="https://wx.network"):
        self.page = page
        self.asset_id = 9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX    # token you’re trading
        self.price_asset_id = EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA  # usually WAVES or USDT
        self.base_url = https://wx.network/trading/spot/9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA

    async def list_open_orders(self):
        """
        Scrape open orders from the 'My Orders' table.
        Returns list of dicts with side/price/amount/order_id.
        """
        trade_url = f"{self.base_url}/trading/spot/{self.asset_id}_{self.price_asset_id}"
        await self.page.goto(trade_url)
        await self.page.wait_for_selector("text=My Orders")

        rows = await self.page.query_selector_all("table:has-text('My Orders') tbody tr")
        orders = []
        for r in rows:
            try:
                tds = await r.query_selector_all("td")
                if len(tds) < 4:
                    continue
                side = (await tds[0].inner_text()).strip().lower()
                price = float((await tds[1].inner_text()).replace(",", "").strip())
                amount = float((await tds[2].inner_text()).replace(",", "").strip())
                order_id = await r.get_attribute("data-row-key")
                orders.append({
                    "id": order_id,
                    "side": side,
                    "price": price,
                    "amount": amount
                })
            except Exception as e:
                print("⚠️ Could not parse order row:", e)
        return orders

    async def cancel_all(self):
        """
        Cancel all open orders by clicking cancel buttons.
        """
        trade_url = f"{self.base_url}/trading/spot/{self.asset_id}_{self.price_asset_id}"
        await self.page.goto(trade_url)
        await self.page.wait_for_selector("text=My Orders")

        cancel_buttons = await self.page.query_selector_all("button:has-text('Cancel')")
        for b in cancel_buttons:
            try:
                await b.click()
                await asyncio.sleep(0.5)
                print("❌ Cancelled one order")
            except Exception as e:
                print("⚠️ Cancel click failed:", e)

    async def place_orders(self, orders):
        """
        Place grid orders (buy/sell) via UI.
        orders: list of Order objects.
        """
        trade_url = f"{self.base_url}/trading/spot/{self.asset_id}_{self.price_asset_id}"
        await self.page.goto(trade_url)
        await self.page.wait_for_selector("input[placeholder='Price']")

        for o in orders:
            print(f"➡️ Placing {o.side.upper()} {o.size} @ {o.price}")

            try:
                # Fill price
                price_box = await self.page.query_selector("input[placeholder='Price']")
                await price_box.fill(str(o.price))

                # Fill amount
                amount_box = await self.page.query_selector("input[placeholder='Amount']")
                await amount_box.fill(str(o.size))

                # Click Buy or Sell
                if o.side.lower() == "buy":
                    await self.page.click("button:has-text('Buy')")
                else:
                    await self.page.click("button:has-text('Sell')")

                # Confirm placement
                try:
                    await self.page.wait_for_selector("text=Order placed", timeout=5000)
                    print("✅ Order confirmed")
                except:
                    print("⚠️ No confirmation detected")

            except Exception as e:
                print("❌ Failed to place order:", e)

            await asyncio.sleep(1)  # spacing to avoid UI race

# Example for manual test
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        wx = WXExchange(page, asset_id="9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX", price_asset_id="EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA")

        await wx.cancel_all()
        open_orders = await wx.list_open_orders()
        print("Open orders:", open_orders)

        from grid import Order
        test_orders = [
            Order(id=None, side="buy", price=0.1, size=5),
            Order(id=None, side="sell", price=0.2, size=5)
        ]
        await wx.place_orders(test_orders)

        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
