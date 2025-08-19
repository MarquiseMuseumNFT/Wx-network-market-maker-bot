from dataclasses import dataclass
from typing import List


@dataclass
class GridOrder:
    price: float
    size: float
    side: str  # "buy" or "sell"

    def to_wx_payload(self):
        """
        Convert GridOrder into WX API order payload (scaled to satoshis).
        """
        return {
            "orderType": "buy" if self.side == "buy" else "sell",
            "amount": int(self.size * 1e8),  # size scaled
            "price": int(self.price * 1e8),  # price scaled
            "matcherFeeAssetId": "WAVES",
        }


def build_grid(mid: float, levels: int, spacing_bps: float, size: float) -> List[GridOrder]:
    """
    Build a symmetric grid around the mid price.
    mid: reference price
    levels: number of orders above and below
    spacing_bps: grid spacing in basis points
    size: order size (in float tokens, not satoshis)
    """
    grid = []
    spacing = spacing_bps / 10000.0
    for i in range(1, levels + 1):
        buy_price = mid * (1 - spacing * i)
        sell_price = mid * (1 + spacing * i)
        grid.append(GridOrder(price=buy_price, size=size, side="buy"))
        grid.append(GridOrder(price=sell_price, size=size, side="sell"))
    return grid


def total_notional(grid: List[GridOrder]) -> float:
    """
    Sum of notional value across all grid orders (in float units).
    """
    return sum(o.price * o.size for o in grid)


def diff_books(current: List[dict], target: List[GridOrder]):
    """
    Compute cancels and creates by comparing live orders vs grid target.
    current: list of dicts (WX open orders)
    target: list of GridOrder
    """
    cancels, creates = [], []

    # Normalize current book
    current_book = {(float(o["price"]) / 1e8, float(o["amount"]) / 1e8, o["orderType"]): o for o in current}

    for g in target:
        key = (round(g.price, 8), round(g.size, 8), "buy" if g.side == "buy" else "sell")
        if key not in current_book:
            creates.append(g)

    # Any current orders not in target should be cancelled
    target_keys = {(round(g.price, 8), round(g.size, 8), "buy" if g.side == "buy" else "sell") for g in target}
    for k, o in current_book.items():
        if k not in target_keys:
            cancels.append(o)

    return cancels, creates
