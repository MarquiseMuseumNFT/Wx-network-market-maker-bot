import asyncio
import json
import time
from typing import List, Tuple

import httpx
import base58
import nacl.signing
import nacl.encoding


class WXExchange:
    """
    Trading adapter for WX Network.
    Uses Ed25519 signing (via pynacl) + Base58 encoding.
    """

    def __init__(
        self,
        target_asset_id: str,
        seed: str,
        private_key: str,
        public_key: str,
        wallet: str,
        login_pass: str,
    ):
        self.base_url = "https://api.wx.network/v1"
        self.target_asset_id = target_asset_id
        self.seed = seed
        self.private_key = private_key
        self.public_key = public_key
        self.wallet = wallet
        self.login_pass = login_pass
        self.client = httpx.AsyncClient(timeout=10.0)

        # Build signing key from private key (base58 string)
        pk_bytes = base58.b58decode(self.private_key)
        self.signing_key = nacl.signing.SigningKey(pk_bytes[:32])  # Ed25519 seed

    async def connect(self):
        # WX API is stateless — sign every request
        return

    async def list_open_orders(self) -> List[Tuple[str, float, float]]:
        """
        Fetch all open orders for this wallet.
        Returns list of (order_id, price, amount).
        """
        url = f"{self.base_url}/matcher/orderbook/{self.target_asset_id}/USDT/publicKey/{self.public_key}"
        r = await self.client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()
        orders = []
        for o in data.get("orders", []):
            price = float(o["price"]) / 1e8
            amount = float(o["amount"]) / 1e8
            orders.append((o["id"], price, amount))
        return orders

    async def cancel_orders(self, order_ids: List[str]):
        """
        Cancel a list of order IDs.
        """
        url = f"{self.base_url}/matcher/orderbook/{self.target_asset_id}/cancel"
        for oid in order_ids:
            payload = {"orderId": oid, "sender": self.wallet}
            headers = self._auth_headers(payload)
            await self.client.post(url, json=payload, headers=headers)

    async def cancel_all(self):
        """
        Cancel all orders in the orderbook for this asset.
        """
        url = f"{self.base_url}/matcher/orderbook/{self.target_asset_id}/cancelAll"
        payload = {"sender": self.wallet}
        headers = self._auth_headers(payload)
        await self.client.post(url, json=payload, headers=headers)

    async def place_orders(self, orders):
        """
        Place multiple orders.
        `orders` = list of tuples (side, price, amount).
        """
        url = f"{self.base_url}/matcher/orderbook"
        for side, price, size in orders:
            payload = {
                "senderPublicKey": self.public_key,
                "matcherPublicKey": "PUT_MATCHER_PUBKEY_HERE",  # TODO: from WX docs
                "assetPair": {
                    "amountAsset": self.target_asset_id,
                    "priceAsset": "USDT",  # adjust if needed
                },
                "orderType": side,  # "buy" or "sell"
                "price": int(price * 1e8),
                "amount": int(size * 1e8),
                "timestamp": int(time.time() * 1000),
                "expiration": int((time.time() + 86400) * 1000),
            }
            headers = self._auth_headers(payload)
            await self.client.post(url, json=payload, headers=headers)

    async def close(self):
        await self.client.aclose()

    def _auth_headers(self, payload: dict) -> dict:
        """
        Sign payload using Ed25519 + Base58.
        WX requires timestamp + signed body.
        """
        ts = str(int(time.time() * 1000))
        body = json.dumps(payload, separators=(",", ":"))
        message = (ts + body).encode()

        signed = self.signing_key.sign(message).signature
        sig_b58 = base58.b58encode(signed).decode()

        return {
            "X-Api-Key": self.public_key,
            "X-Api-Signature": sig_b58,
            "X-Api-Timestamp": ts,
        }
