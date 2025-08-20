def build_grid(mid, levels, spacing_bps, size):
    """
    Build a symmetric grid of buy/sell orders around mid.
    Returns list[dict] with keys: side, price, amount.
    """
    orders = []
    spacing = spacing_bps / 10000.0

    for i in range(1, levels + 1):
        # buy below mid
        buy_price = mid * (1 - i * spacing)
        orders.append({
            "id": None,
            "side": "buy",
            "price": buy_price,
            "amount": size,
        })

        # sell above mid
        sell_price = mid * (1 + i * spacing)
        orders.append({
            "id": None,
            "side": "sell",
            "price": sell_price,
            "amount": size,
        })

    return orders


def total_notional(orders):
    return sum(o["price"] * o["amount"] for o in orders)


def diff_books(current, target, price_tol=1e-8, size_tol=1e-8):
    """
    Compare current exchange orders vs target grid.
    Returns (cancels, creates).
    
    current: from WXExchange.list_open_orders()
             list of dicts {id, side, price, amount}
    target: from build_grid()
             list of dicts {id, side, price, amount}
    """
    cancels = []
    creates = []

    matched = set()
    for t in target:
        found = False
        for c in current:
            if (
                c["side"] == t["side"]
                and abs(c["price"] - t["price"]) < price_tol
                and abs(c["amount"] - t["amount"]) < size_tol
            ):
                matched.add(c["id"])
                found = True
                break
        if not found:
            creates.append(t)

    for c in current:
        if c["id"] not in matched:
            cancels.append(c["id"])

    return cancels, creates
