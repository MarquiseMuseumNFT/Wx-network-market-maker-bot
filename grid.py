from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class GridOrder:
    price: float
    size: float
    side: str   # 'buy' or 'sell'

def build_grid(mid: float, levels: int, spacing_bps: float, size: float) -> List[GridOrder]:
    """Build symmetric grid around `mid` with `levels` on each side."""
    bps = spacing_bps / 10_000.0
    orders: List[GridOrder] = []
    # Buys below mid
    for i in range(1, levels + 1):
        p = mid * (1.0 - bps * i)
        orders.append(GridOrder(price=p, size=size, side="buy"))
    # Sells above mid
    for i in range(1, levels + 1):
        p = mid * (1.0 + bps * i)
        orders.append(GridOrder(price=p, size=size, side="sell"))
    return orders

def total_notional(orders: List[GridOrder]) -> float:
    return sum(abs(o.price * o.size) for o in orders)

def diff_books(current: List[Tuple[str, float, float]], target: List[GridOrder]):
    """
    Compare current open orders vs target grid and produce:
    - cancels: list of order_ids to cancel
    - creates: list of GridOrder to create

    current format: [(order_id, price, size), ...]
    This is simplistic (price exact match). You may want fuzzy matching by tick/size.
    """
    current_map = {(round(p, 8), round(s, 8)): oid for oid, p, s in current}
    target_keys = {(round(o.price, 8), round(o.size, 8)) for o in target}
    cancels = [oid for (p, s), oid in current_map.items() if (p, s) not in target_keys]
    creates = [o for o in target if (round(o.price,8), round(o.size,8)) not in current_map]
    return cancels, creates