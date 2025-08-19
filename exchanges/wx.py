import aiohttp
import logging
from grid import GridOrder

logger = logging.getLogger("wx")

class WXExchange:
    """
    WX Exchange spot trading adapter (no matcher).
    Works with unlisted tokens by using raw spot API.
    """

    BASE_URL = "https://wx.network/api/v1"

    def __init__(self, target_asset_id, seed, private_key, public_key, wallet, login_pass):
        self.target_asset_id = target_asset_id
        self.seed = seed
        self.private_key = private_key
        self.public_key = public_key
        self.wallet = wallet
        self.login_pass = login_pass
        self.session = None

        # Hardcode asset pair IDs for Saureus/Splatinum
        self.base_asset = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX"   # Saureus
        self.quote_asset = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"   # Splatinum

    async def connect(self):
        self.session = aiohttp.ClientSession()
        logger.info("Connected to WX API session")

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Closed WX session")

    async def list_open_orders(self):
        """
        Get open orders for this trading pair.
        """
        url = f"{self.BASE_URL}/trades/{self.base_asset}/{self.quote_asset}/orders/active"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    logger.error(f"list_open_orders error {resp.status}: {txt}")
                    return []
                data = await resp.json()
                # Convert to GridOrder-like dicts
                return [
                    GridOrder(price=float(o["price"]),
                              size=float(o["amount"]),
                              side=o["side"])
                    for o in data.get("data", [])
                ]
        except Exception as e:
            logger.error(f"list_open_orders exception: {e}")
            return []

    async def cancel_orders(self, orders):
        """
        Cancel multiple orders by IDs.
        """
        for order in orders:
            try:
                url = f"{self.BASE_URL}/order/cancel/{order.id}"
                async with self.session.post(url) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error(f"Cancel failed {resp.status}: {txt}")
                    else:
                        logger.info(f"Cancelled order {order.id}")
            except Exception as e:
                logger.error(f"Cancel order error: {e}")

    async def cancel_all(self):
        """
        Cancel ALL open orders.
        """
        current = await self.list_open_orders()
        await self.cancel_orders(current)

    async def place_orders(self, orders):
        """
        Place multiple GridOrders.
        """
        url = f"{self.BASE_URL}/order"
        placed = 0
        for o in orders:
            payload = {
                "amount": str(o.size),
                "price": str(o.price),
                "side": o.side,
                "baseAsset": self.base_asset,
                "quoteAsset": self.quote_asset,
                "orderType": "limit"
            }
            try:
                async with self.session.post(url, json=payload) as resp:
                    txt = await resp.text()
                    if resp.status != 200:
                        logger.error(f"Place order failed {resp.status}: {txt}")
                    else:
                        logger.info(f"Placed order {o.side} {o.size}@{o.price}")
                        placed += 1
            except Exception as e:
                logger.error(f"place_orders error: {e}")
        return placed
