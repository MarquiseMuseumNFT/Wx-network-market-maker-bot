import aiohttp
import logging
import os

log = logging.getLogger("wx")

class WXExchange:
    def __init__(self, target_asset_id: str):
        self.base_url = "https://api.wx.network/api/v1"
        self.target_asset_id = target_asset_id
        self.api_token = os.getenv("WX_API_KEY")  # set this in Render env vars
        self.session: aiohttp.ClientSession | None = None

    async def connect(self):
        """Attach Authorization header with existing JWT (no login)."""
        if not self.api_token:
            raise Exception("Missing WX_API_KEY (JWT token) in env vars")

        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_token}"}
        )
        log.info("Connected to WX API session with provided token")

    async def close(self):
        if self.session:
            await self.session.close()

    async def list_open_orders(self):
        """Fetch open orders for current market."""
        try:
            async with self.session.get(f"{self.base_url}/orders/active") as r:
                text = await r.text()
                if r.status != 200:
                    log.error(f"list_open_orders error {r.status}: {text}")
                    return []
                data = await r.json()
                return data.get("orders", [])
        except Exception as e:
            log.error(f"list_open_orders exception: {e}")
            return []

    async def place_orders(self, orders):
        """Place multiple limit orders on this market."""
        payload = []
        for o in orders:
            side = "BUY" if o.side.lower() == "buy" else "SELL"
            payload.append({
                "symbol": self.target_asset_id,
                "side": side,
                "price": str(o.price),
                "quantity": str(o.size),
                "type": "LIMIT",
                "timeInForce": "GTC"
            })

        try:
            async with self.session.post(f"{self.base_url}/orders/batch", json=payload) as r:
                text = await r.text()
                if r.status != 200:
                    log.error(f"Place order failed {r.status}: {text}")
                return await r.json()
        except Exception as e:
            log.error(f"place_orders exception: {e}")
            return None

    async def cancel_orders(self, order_ids):
        """Cancel multiple orders by IDs."""
        try:
            async with self.session.post(
                f"{self.base_url}/orders/cancel",
                json={"orderIds": order_ids},
            ) as r:
                text = await r.text()
                if r.status != 200:
                    log.error(f"cancel_orders failed {r.status}: {text}")
                return await r.json()
        except Exception as e:
            log.error(f"cancel_orders exception: {e}")
            return None

    async def cancel_all(self):
        """Cancel all open orders."""
        orders = await self.list_open_orders()
        ids = [o["id"] for o in orders]
        if ids:
            await self.cancel_orders(ids)
