import requests
import json
import websockets
import gzip
import asyncio
import logging

logger = logging.getLogger(__name__)


class HTXExchange:
    """
    Simple REST client for HTX (Huobi) depth snapshots.
    Useful for quick price checks.
    """

    BASE_URL = "https://api-aws.huobi.pro"

    def __init__(self, symbol="wavesusdt"):
        self.symbol = symbol.lower()

    def get_mid_price(self):
        """
        Fetch order book snapshot and calculate mid price.
        """
        try:
            url = f"{self.BASE_URL}/market/depth?symbol={self.symbol}&type=step0"
            resp = requests.get(url, timeout=5).json()
            bids = resp["tick"]["bids"]
            asks = resp["tick"]["asks"]
            if not bids or not asks:
                return None
            best_bid = bids[0][0]
            best_ask = asks[0][0]
            return (best_bid + best_ask) / 2
        except Exception as e:
            logger.error(f"HTX REST price fetch failed: {e}")
            return None


class HTXMarketData:
    """
    Realtime market data (mid price) from HTX WebSocket.
    """

    def __init__(self, symbol: str):
        # HTX uses lowercase + no underscore (e.g. "wavesusdt")
        self.symbol = symbol.lower().replace("_", "")
        self._ws = None
        self._mid = None

    async def connect(self):
        """
        Connect to HTX websocket and subscribe to depth feed.
        """
        self._ws = await websockets.connect("wss://api.huobi.pro/ws")
        sub_msg = {"sub": f"market.{self.symbol}.depth.step0", "id": "1"}
        await self._ws.send(json.dumps(sub_msg))
        asyncio.create_task(self._reader())
        logger.info(f"Subscribed to HTX depth feed for {self.symbol}")

    async def _reader(self):
        """
        Internal: read WS messages and update mid price.
        """
        while True:
            try:
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    msg = gzip.decompress(raw).decode("utf-8")
                else:
                    msg = raw
                data = json.loads(msg)

                if "ping" in data:
                    await self._ws.send(json.dumps({"pong": data["ping"]}))
                    continue

                if "tick" in data:
                    tick = data["tick"]
                    bids = tick.get("bids", [])
                    asks = tick.get("asks", [])
                    if bids and asks:
                        best_bid = bids[0][0]
                        best_ask = asks[0][0]
                        self._mid = (float(best_bid) + float(best_ask)) / 2.0
            except Exception as e:
                logger.error(f"HTX WS reader error: {e}")
                await asyncio.sleep(1)

    async def mid_price(self):
        """
        Return the latest mid price (or None if not yet available).
        """
        return self._mid

    async def close(self):
        """
        Close websocket connection.
        """
        if self._ws:
            await self._ws.close()
            self._ws = None
