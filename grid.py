from dataclasses import dataclass

@dataclass
class GridOrder:
    side: str      # "buy" or "sell"
    price: float
    size: float

def build_grid(mid_price: float, levels: int, spacing_bps: float, order_size: float):
    """
    Build a symmetric grid of buy/sell orders around mid_price.
    - spacing_bps = distance between levels in basis points (0.01%).
    """
    grid = []
    spacing = spacing_bps / 10000.0

    for i in range(1, levels + 1):
        # Buy levels below mid
        buy_price = mid_price * (1 - spacing * i)
        grid.append(GridOrder(side="buy", price=round(buy_price, 8), size=order_size))

        # Sell levels above mid
        sell_price = mid_price * (1 + spacing * i)
        grid.append(GridOrder(side="sell", price=round(sell_price, 8), size=order_size))

    return grid

def total_notional(grid):
    """
    Compute total notional exposure (sum of price*size).
    """
    return sum(o.price * o.size for o in grid)

def diff_books(current, target):
    """
    Compare current open orders with target grid.
    Returns: (cancels, creates)
    """
    cancels = []
    creates = []

    # Map current orders by price + side for comparison
    current_map = {(float(o.get("price")), o.get("side").lower()): o for o in current}

    for g in target:
        key = (float(g.price), g.side.lower())
        if key not in current_map:
            creates.append(g)

    for k, order in current_map.items():
        if not any(abs(g.price - k[0]) < 1e-8 and g.side.lower() == k[1] for g in target):
            cancels.append(order.get("id"))

    return cancels, creates
