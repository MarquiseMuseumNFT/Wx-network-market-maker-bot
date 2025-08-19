import aiohttp
import asyncio
import logging

log = logging.getLogger("wx-exchange")

# Saureus (waves mimic)
SAUREUS_ASSET_ID = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"
# Splatinum (usdt mimic)
SPLATINUM_ASSET_ID = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"

WX_NODE = "https://nodes.wavesnodes.com"
WX_MATCHER = "https://matcher.waves.exchange"

class WXExchange:
    def __init__(self, target_asset_id, seed, private_key, public_key, wallet, login_pass):
        self.target_asset_id = target_asset_id
        self.seed = seed
        self.private_key = private_key
        self.public_key = public_key
        self.wallet = wallet
        self.login_pass = login_pass
        self.session: aiohttp.ClientSession | None = None
        self.base_asset = SAUREUS_ASSET_ID
        self.quote_asset = SPLATINUM_ASSET_ID

    async def connect(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
            log.info("Connected to WX API session")

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
            log.info("Closed WX API session")

    async def list_open_orders(self):
        url = f"{WX_MATCHER}/matcher/orderbook/{self.base_asset}/{self.quote_asset}/publicKey/{self.public_key}"
        async with self.session.get(url) as resp:
            if resp.status != 200:
                text = await resp.text()
                log.error(f"list_open_orders error {resp.status}: {text}")
                return []
            data = await resp.json()
            return data.get("orders", [])

    async def cancel_orders(self, orders):
        for order in orders:
            order_id = order.get("id")
            if not order_id:
                continue
            url = f"{WX_MATCHER}/matcher/orderbook/{self.base_asset}/{self.quote_asset}/cancel"
            payload = {"orderId": order_id, "sender": self.public_key}
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    log.error(f"Cancel order {order_id} failed {resp.status}: {text}")
                else:
                    log.info(f"Cancelled order {order_id}")

    async def cancel_all(self):
        current = await self.list_open_orders()
        await self.cancel_orders(current)

    async def place_orders(self, orders):
        for g in orders:
            url = f"{WX_MATCHER}/matcher/orderbook"
            payload = {
                "amountAsset": self.base_asset,
                "priceAsset": self.quote_asset,
                "orderType": "buy" if g.side == "buy" else "sell",
                "price": int(g.price * 10**6),  # assuming 6 decimals
                "amount": int(g.size * 10**6),
                "sender": self.public_key,
            }
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    log.error(f"Place order failed {resp.status}: {text}")
                else:
                    log.info(f"Placed {g.side} {g.size}@{g.price}")
