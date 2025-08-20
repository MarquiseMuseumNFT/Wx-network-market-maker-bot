import asyncio
from exchanges.wx import WXExchange
from config import settings


async def main():
    wx = WXExchange(settings)

    print("🔌 Connecting to WX...")
    await wx.connect()

    print("📋 Fetching open orders...")
    orders = await wx.list_open_orders()

    if not orders:
        print("⚠️ No open orders found.")
    else:
        for o in orders:
            print(f"ID={o.id}, Side={o.side}, Price={o.price}, Size={o.size}")

    await wx.close()
    print("✅ Done")


if __name__ == "__main__":
    asyncio.run(main())
