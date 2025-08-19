import aiohttp
import asyncio
import logging

log = logging.getLogger("wx")

class WXExchange:
    def __init__(self, target_asset_id, seed, private_key, public_key,
                 wallet, login_pass, base_url="https://api.wx.network/api"):
        self.base_url = base_url.rstrip("/")
        self.target_asset_id = target_asset_id
        self.seed = seed
        self.private_key = private_key
        self.public_key = public_key
        self.wallet = wallet
        self.login_pass = login_pass
        self.api_token = None
        self.session: aiohttp.ClientSession | None = None

    async def connect(self):
        """Authenticate and create session with Authorization header."""
        async with aiohttp.ClientSession() as s:
            resp = await s.post(
                f"{self.base_url}/v1/auth/session",
                json={"login": self.wallet, "password": self.login_pass},
            )
            data = await resp.json()
            if "token" not in data:
                raise Exception(f"Auth failed: {data}")
            self.api_token = data["token"]

        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_token}"}
        )
        log.info("Connected to WX API session")

    async def close(self):
        if self.session:
            await self.session.close()

    async def list_open_orders(self):
        """Fetch open orders."""
        try:
            async with self.session.get(f"{self.base_url}/v1/orders") as r:
                data = await r.json()
                if r.status != 200:
                    log.error(f"list_open_orders error {r.status}: {data}")
                    return []
                return data.get("orders", [])
        except Exception as e:
            log.error(f"list_open_orders exception: {e}")
            return []

    async def place_orders(self, orders):
        """Place multiple limit orders."""
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
            async with self.session.post(f"{self.base_url}/v1/orders/batch", json=payload) as r:
                data = await r.json()
                if r.status != 200:
                    log.error(f"Place order failed {r.status}: {data}")
                return data
        except Exception as e:
            log.error(f"place_orders exception: {e}")
            return None

    async def cancel_orders(self, order_ids):
        """Cancel multiple orders."""
        try:
            async with self.session.post(
                f"{self.base_url}/v1/orders/cancel",
                json={"orderIds": order_ids},
            ) as r:
                data = await r.json()
                if r.status != 200:
                    log.error(f"cancel_orders failed {r.status}: {data}")
                return data
        except Exception as e:
            log.error(f"cancel_orders exception: {e}")
            return None

    async def cancel_all(self):
        """Cancel all active orders."""
        orders = await self.list_open_orders()
        ids = [o["id"] for o in orders]
        if ids:
            await self.cancel_orders(ids)
