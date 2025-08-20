from playwright.async_api import async_playwright

class WXExchange:
    def __init__(self, config):
        self.browser = None
        self.page = None
        self.playwright = None
        self.config = config

    async def connect(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)  # set True on server
        self.page = await self.browser.new_page()
        await self.page.goto("https://wx.network/")

        # Click login
        await self.page.get_by_text("Sign In").click()

        # Fill password
        await self.page.fill("input[type='password']", self.config.wx_login_pass)

        # Submit form (by pressing Enter or clicking button)
        await self.page.press("input[type='password']", "Enter")

        # Wait for balance or orders panel to show up
        await self.page.wait_for_selector("text=Balance")

    async def place_order(self, side: str, price: float, amount: float):
        await self.page.goto("https://wx.network/trading/spot/9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA")

        # Fill order form
        await self.page.fill("input[name='price']", str(price))
        await self.page.fill("input[name='amount']", str(amount))

        # Submit order
        if side.lower() == "buy":
            await self.page.get_by_role("button", name="Buy").click()
        else:
            await self.page.get_by_role("button", name="Sell").click()

        # Confirm
        await self.page.get_by_role("button", name="Confirm").click()

    async def place_orders(self, orders):
        """Place multiple grid orders"""
        for o in orders:
            await self.place_order(o.side, o.price, o.size)

    async def cancel_orders(self, orders):
        """Cancel specific orders by id"""
        await self.page.goto("https://wx.network/orders/open")

        for o in orders:
            # Each order should have an .id or identifier
            selector = f"text=Cancel >> [data-order-id='{o.id}']"
            try:
                btn = await self.page.query_selector(selector)
                if btn:
                    await btn.click()
            except Exception:
                pass

    async def cancel_all(self):
        """Cancel all open orders"""
        await self.page.goto("https://wx.network/orders/open")
        cancel_buttons = await self.page.query_selector_all("text=Cancel")
        for btn in cancel_buttons:
            await btn.click()

    async def list_open_orders(self):
        """Scrape open orders table and return as list of dicts"""
        await self.page.goto("https://wx.network/orders/open")

        rows = await self.page.query_selector_all("table tr")
        orders = []
        for row in rows:
            cells = await row.query_selector_all("td")
            if not cells:
                continue
            try:
                order = {
                    "id": await cells[0].inner_text(),   # adjust index depending on table layout
                    "side": await cells[1].inner_text(),
                    "price": float(await cells[2].inner_text()),
                    "size": float(await cells[3].inner_text()),
                }
                orders.append(order)
            except Exception:
                continue
        return orders

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
