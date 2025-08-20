from dataclasses import dataclass

@dataclass
class Order:
    id: str | None     # exchange order id, None for grid-generated orders
    side: str          # "buy" or "sell"
    price: float
    size: float


def build_grid(mid, levels, spacing_bps, size):
    """
    Build a symmetric grid of buy/sell orders around mid.
    Returns list[Order].
    """
    orders = []
    spacing = spacing_bps / 10000.0

    for i in range(1, levels + 1):
        # buy below mid
        buy_price = mid * (1 - i * spacing)
        orders.append(Order(id=None, side="buy", price=buy_price, size=size))

        # sell above mid
        sell_price = mid * (1 + i * spacing)
        orders.append(Order(id=None, side="sell", price=sell_price, size=size))

    return orders


def total_notional(orders):
    return sum(o.price * o.size for o in orders)


def diff_books(current, target, price_tol=1e-8, size_tol=1e-8):
    """
    Compare current exchange orders vs target grid.
    Returns (cancels, creates).
    """
    cancels = []
    creates = []

    matched = set()
    for t in target:
        found = False
        for c in current:
            if (
                c.side == t.side
                and abs(c.price - t.price) < price_tol
                and abs(c.size - t.size) < size_tol
            ):
                matched.add(c.id)
                found = True
                break
        if not found:
            creates.append(t)

    for c in current:
        if c.id not in matched:
            cancels.append(c)

    return cancels, creates
