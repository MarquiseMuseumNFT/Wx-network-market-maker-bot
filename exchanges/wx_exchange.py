import asyncio

class WXExchange:
    def __init__(self, page, base_url="https://wx.network"):
        self.page = page
        self.asset_id = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"    # base token
        self.price_asset_id = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"  # quote token (USDT/WAVES)
        self.base_url = base_url

    async def goto_market(self):
        """Navigate directly to the hardcoded trading pair page."""
        url = f"{self.base_url}/trading/spot/{self.asset_id}_{self.price_asset_id}"
        await self.page.goto(url)
        print(f"Opened market: {url}")

    async def debug_selectors(self):
        """Print all input and button selectors currently visible."""
        inputs = await self.page.query_selector_all("input")
        buttons = await self.page.query_selector_all("button")

        print("\n--- DEBUG: INPUTS ---")
        for i, el in enumerate(inputs):
            try:
                html = await el.get_attribute("outerHTML")
                print(f"[{i}] {html[:120]}...")
            except:
                pass

        print("\n--- DEBUG: BUTTONS ---")
        for i, el in enumerate(buttons):
            try:
                text = await el.inner_text()
                html = await el.get_attribute("outerHTML")
                print(f"[{i}] Text='{text.strip()}' | {html[:120]}...")
            except:
                pass
        print("\n⚠️ Use these to identify correct selectors for price, amount, buy, sell.\n")

    async def place_order(self, side: str, price: float, amount: float):
        """
        Place a BUY or SELL order on WX frontend.
        side = 'buy' or 'sell'
        """
        print(f"Placing {side.upper()} order: {amount} at {price}")

        # Candidate selectors for inputs
        price_selectors = ["input[name='price']", "input[placeholder*='Price']", "input[data-testid='price']"]
        amount_selectors = ["input[name='amount']", "input[placeholder*='Amount']", "input[data-testid='amount']"]

        # Fill price
        filled = False
        for sel in price_selectors:
            try:
                await self.page.fill(sel, str(price))
                print(f"✅ Filled price using selector: {sel}")
                filled = True
                break
            except:
                continue
        if not filled:
            print("⚠️ Could not find price input. Run debug_selectors() to inspect.")

        # Fill amount
        filled = False
        for sel in amount_selectors:
            try:
                await self.page.fill(sel, str(amount))
                print(f"✅ Filled amount using selector: {sel}")
                filled = True
                break
            except:
                continue
        if not filled:
            print("⚠️ Could not find amount input. Run debug_selectors() to inspect.")

        # Candidate selectors for Buy/Sell buttons
        if side == "buy":
            btn_selectors = ["button:has-text('Buy')", "button.buy", "button.bg-green-500"]
        elif side == "sell":
            btn_selectors = ["button:has-text('Sell')", "button.sell", "button.bg-red-500"]
        else:
            print("❌ Invalid side, must be 'buy' or 'sell'")
            return

        clicked = False
        for sel in btn_selectors:
            try:
                await self.page.click(sel)
                print(f"✅ Clicked {side.upper()} button using selector: {sel}")
                clicked = True
                break
            except:
                continue
        if not clicked:
            print(f"⚠️ Could not find {side.upper()} button. Run debug_selectors() to inspect.")
