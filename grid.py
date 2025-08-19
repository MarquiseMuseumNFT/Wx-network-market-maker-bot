import uuid
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GridOrder:
    """
    Represents a single grid order.
    """
    price: float
    size: float
    side: str   # "buy" or "sell"
    id: str = None  # unique order ID

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())  # auto-generate if not set


def build_grid(mid_price: float, levels: int, spacing_bps: float, size: float) -> List[GridOrder]:
    """
    Build symmetric grid orders around mid price.
    """
    grid: List[GridOrder] = []
    spacing = spacing_bps / 10000  # bps -> decimal

    for i in range(1, levels + 1):
        # Buy order below mid
        buy_price = mid_price * (1 - spacing * i)
        grid.append(GridOrder(price=buy_price, size=size, side="buy"))

        # Sell order above mid
        sell_price = mid_price * (1 + spacing * i)
        grid.append(GridOrder(price=sell_price, size=size, side="sell"))

    return grid


def total_notional(orders: List[GridOrder]) -> float:
    """
    Compute notional value of all orders.
    """
    return sum(o.price * o.size for o in orders)


def diff_books(current: List[GridOrder], target: List[GridOrder]) -> Tuple[List[GridOrder], List[GridOrder]]:
    """
    Compare currently active orders vs target grid.
    Returns (cancels, creates).
    """
    cancels: List[GridOrder] = []
    creates: List[GridOrder] = []

    # Index by (price, side) since exchange may round IDs
    current_map = {(round(o.price, 6), o.side): o for o in current}
    target_map = {(round(o.price, 6), o.side): o for o in target}

    # Orders to cancel (in current but not in target)
    for key, order in current_map.items():
        if key not in target_map:
            cancels.append(order)

    # Orders to create (in target but not in current)
    for key, order in target_map.items():
        if key not in current_map:
            creates.append(order)

    return cancels, creates
