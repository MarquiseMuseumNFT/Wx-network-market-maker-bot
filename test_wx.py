import asyncio
from exchanges.wx import WXExchange
from config import settings


async def main():
    wx = WXExchange(settings)

    print("🔌 Connecting to WX...")
    await wx.connect()

    try:
        print("📋 Fetching open orders...")
        orders = await wx.list_open_orders()

        if not orders:
            print("⚠️ No structured orders found, trying raw rows for debug...")
            rows = await wx.page.query_selector_all("table tr")
            for i, row in enumerate(rows):
                text = await row.inner_text()
                print(f"ROW {i}: {text}")
        else:
            for o in orders:
                print(f"ID={o.id}, Side={o.side}, Price={o.price}, Size={o.size}")

        # 📸 Take screenshot of orders area
        table = await wx.page.query_selector("table")
        if table:
            await table.screenshot(path="orders.png")
            print("🖼 Saved screenshot: orders.png")
        else:
            await wx.page.screenshot(path="orders.png", full_page=True)
            print("🖼 Saved full-page screenshot: orders.png")

    finally:
        await wx.close()
        print("✅ Done")


if __name__ == "__main__":
    asyncio.run(main())
