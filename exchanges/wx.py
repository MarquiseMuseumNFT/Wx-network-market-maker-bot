import aiohttp
import logging
import asyncio

logger = logging.getLogger(__name__)

BASE_URL = "https://api.wx.network/v1"

class WXExchange:
    """
    Minimal WX REST adapter (no matcher).
    Uses spot trading endpoints for custom asset pairs (e.g. Saureus/Splatinum).
    """

    def __init__(self, target_asset_id: str, seed=None, private_key=None, public_key=None,
                 wallet=None, login_pass=None):
        self.target_asset_id = target_asset_id
        self.base_asset_id = "WAVES"  # Saureus mimic is Waves
        self.quote_asset_id = "EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"  # Splatinum mimic of USDT
        self.session = None

    async def connect(self):
        self.session = aiohttp.ClientSession()
        logger.info("Connected to WX API session")

    async def close(self):
        if self.session:
            await self.session.close()
            logger.info("Closed WX API session")

    async def list_open_orders(self):
        """
        Fetch open orders for this pair.
        """
        url = f"{BASE_URL}/orderbook/{self.target_asset_id}/{self.quote_asset_id}/public"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    logger.error(f"list_open_orders error {resp.status}: {txt}")
                    return []
                data = await resp.json()
                return data.get("orders", [])
        except Exception as e:
            logger.error(f"list_open_orders exception: {e}")
            return []

    async def cancel_orders(self, orders):
        """
        Cancel specific orders.
        """
        results = []
        for o in orders:
            try:
                url = f"{BASE_URL}/orderbook/{self.target_asset_id}/{self.quote_asset_id}/cancel"
                payload = {"orderId": o.id}
                async with self.session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error(f"Cancel order {o.id} failed {resp.status}: {txt}")
                    else:
                        results.append(await resp.json())
            except Exception as e:
                logger.error(f"Cancel order {o.id} exception: {e}")
        return results

    async def cancel_all(self):
        """
        Cancel all open orders.
        """
        current = await self.list_open_orders()
        if not current:
            return []
        return await self.cancel_orders(current)

    async def place_orders(self, orders):
        """
        Place multiple grid orders via WX spot API.
        orders: list of GridOrder(price, size, side)
        """
        results = []
        for o in orders:
            try:
                url = f"{BASE_URL}/orderbook/{self.target_asset_id}/{self.quote_asset_id}/place"
                payload = {
                    "orderType": "buy" if o.side == "buy" else "sell",
                    "amount": int(o.size * 1e8),  # convert to satoshis
                    "price": int(o.price * 1e8),  # convert to satoshis
                    "matcherFeeAssetId": "WAVES",
                }
                async with self.session.post(url, json=payload) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error(f"Place order failed {resp.status}: {txt}")
                    else:
                        results.append(await resp.json())
            except Exception as e:
                logger.error(f"place_orders exception: {e}")
        return results
