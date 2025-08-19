import requests
import logging

logger = logging.getLogger(__name__)

class HTXMarketData:
    BASE_URL = "https://api-aws.huobi.pro"

    def __init__(self, symbol: str):
        # Example input: "waves-usdt" → "wavesusdt"
        self.symbol = symbol.lower().replace("-", "")

    async def connect(self):
        logger.info(f"[HTX] Using REST polling for {self.symbol}")

    async def mid_price(self):
        try:
            url = f"{self.BASE_URL}/market/depth?symbol={self.symbol}&type=step0"
            resp = requests.get(url, timeout=5).json()

            if "tick" not in resp or "bids" not in resp["tick"] or "asks" not in resp["tick"]:
                logger.warning(f"[HTX] No order book data for {self.symbol}")
                return None

            bids = resp["tick"]["bids"]
            asks = resp["tick"]["asks"]

            if not bids or not asks:
                logger.warning(f"[HTX] Empty bids/asks for {self.symbol}")
                return None

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid = (best_bid + best_ask) / 2.0
            logger.debug(f"[HTX] Mid price for {self.symbol}: {mid}")
            return mid

        except Exception as e:
            logger.error(f"[HTX] REST fetch failed for {self.symbol}: {e}")
            return None

    async def close(self):
        logger.info("[HTX] REST adapter closed")
        pass
