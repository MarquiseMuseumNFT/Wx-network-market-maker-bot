import requests
import logging

logger = logging.getLogger(__name__)

class HTXExchange:
    BASE_URL = "https://api-aws.huobi.pro"

    def __init__(self, symbol="wavesusdt"):
        self.symbol = symbol.lower()

    def get_mid_price(self):
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
            logger.error(f"HTX price fetch failed: {e}")
            return None


    async def connect(self):
        # ✅ Official HTX websocket endpoint
        self._ws = await websockets.connect("wss://api.huobi.pro/ws")

        # ✅ Correct subscription message
        sub_msg = {"sub": f"market.{self.symbol}.ticker", "id": "1"}
        await self._ws.send(json.dumps(sub_msg))

        # Spawn reader loop
        asyncio.create_task(self._reader())

    async def _reader(self):
        while True:
            try:
                # HTX sends gzip-compressed messages
                raw = await self._ws.recv()
                if isinstance(raw, bytes):
                    msg = gzip.decompress(raw).decode("utf-8")
                else:
                    msg = raw
                data = json.loads(msg)

                # Handle ping-pong heartbeat
                if "ping" in data:
                    await self._ws.send(json.dumps({"pong": data["ping"]}))
                    continue

                # ✅ Parse ticker data
                if "tick" in data:
                    tick = data["tick"]
                    best_bid = tick.get("bid", [None])[0]  # bid is a list [price, size]
                    best_ask = tick.get("ask", [None])[0]
                    if best_bid and best_ask:
                        self._mid = (float(best_bid) + float(best_ask)) / 2.0

            except Exception as e:
                print("Reader error:", e)
                await asyncio.sleep(1)

    async def mid_price(self):
        return self._mid

    async def close(self):
        if self._ws:
            await self._ws.close()
