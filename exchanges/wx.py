from playwright.async_api import async_playwright

class WXExchange:
    def __init__(self, config):
        self.browser = None
        self.page = None
        self.playwright = None
        self.config = config

    async def connect(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)  # set True for server
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

    async def cancel_all_orders(self):
        await self.page.goto("https://wx.network/orders/open")
        cancel_buttons = await self.page.query_selector_all("text=Cancel")
        for btn in cancel_buttons:
            await btn.click()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
