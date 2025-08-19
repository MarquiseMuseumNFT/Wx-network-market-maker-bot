import asyncio
import json
import websockets
import time

class HTXMarketData:
    """Reference market data (e.g., WAVES_USDT on HTX). 
    TODO: Replace with the official HTX WS endpoint and subscription message."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self._ws = None
        self._mid = None

    async def connect(self):
        # TODO: put actual HTX websocket URL (public market data)
        self._ws = await websockets.connect("wss://example-htx-ws/marketdata")
        # TODO: send proper subscribe for best bid/ask or ticker for self.symbol
        sub_msg = {"op": "sub", "topic": f"ticker.{self.symbol}"}
        await self._ws.send(json.dumps(sub_msg))

        asyncio.create_task(self._reader())

    async def _reader(self):
        while True:
            try:
                msg = await self._ws.recv()
                data = json.loads(msg)
                # TODO: parse best bid/ask from HTX payload
                best_bid = data.get("best_bid") or data.get("bid")
                best_ask = data.get("best_ask") or data.get("ask")
                if best_bid and best_ask:
                    self._mid = (float(best_bid) + float(best_ask)) / 2.0
            except Exception:
                await asyncio.sleep(1)

    async def mid_price(self):
        return self._mid

    async def close(self):
        if self._ws:
            await self._ws.close()