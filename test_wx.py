import asyncio
from exchanges.wx import WXExchange
import settings
from grid import Order   # using your dataclass Order

async def main():
    wx = WXExchange(settings)
    await wx.connect()

    # Step 1: list open orders
    open_orders = await wx.list_open_orders()
    print("📋 Open orders:", open_orders)

    # Step 2: cancel all
    if open_orders:
        print("⚠️ Cancelling all existing orders...")
        await wx.cancel_all()

    # Step 3: place 1 buy + 1 sell
    test_orders = [
        Order(id=None, side="buy", price=0.5, size=1),   # adjust values to fit market tick size
        Order(id=None, side="sell", price=2.0, size=1),
    ]
    print("📝 Placing test orders...")
    await wx.place_orders(test_orders)

    # Step 4: close session
    await wx.close()

if __name__ == "__main__":
    asyncio.run(main())
