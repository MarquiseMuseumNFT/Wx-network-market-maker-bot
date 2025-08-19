import asyncio
import json
import websockets
import gzip

class HTXMarketData:
    """Reference market data (e.g., WAVES_USDT on HTX)."""

    def __init__(self, symbol: str):
        # HTX symbols are lowercase, no underscore, e.g. "wavesusdt"
        self.symbol = symbol.lower().replace("_", "")
        self._ws = None
        self._mid = None

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
