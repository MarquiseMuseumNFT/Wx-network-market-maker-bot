from exchanges.wx_exchange import WXExchange
from grid import build_grid, total_notional, diff_books

if __name__ == "__main__":
    wx = WXExchange()

    # Pick a trading pair
    pair = "9RVjakuEc6dzBtyAwTTx43ChP8ayFBpbM1KEpJK82nAX_EikmkCRKhPD7Bx9f3avJkfiJMXre55FPTyaG8tffXfA"   # <-- change this to your real pair

    # Get current market data
    ticker = wx.get_ticker(pair)
    mid = (ticker["best_bid"] + ticker["best_ask"]) / 2
    print(f"Mid price for {pair}: {mid}")

    # Build grid
    grid = build_grid(mid=mid, levels=3, spacing_bps=100, size=1)  # size = order amount
    print("\nTarget Grid Orders:")
    for o in grid:
        print(o)

    print("\nTotal notional:", total_notional(grid))

    # Get current open orders
    current = wx.list_open_orders(pair)
    print("\nCurrent orders:", current)

    # Diff between what we want vs what exists
    cancels, creates = diff_books(current, grid)
    print("\nCancelling:", cancels)
    print("Creating:", creates)

    # Cancel old orders
    for oid in cancels:
        wx.cancel_order(pair, oid)

    # Place new orders
    for o in creates:
        wx.place_order(pair, o["side"], o["price"], o["amount"])

    print("\n✅ Grid synced with live exchange!")
