import asyncio
from exchanges.wx import WXExchange

async def main():
    wx = WXExchange(target_asset_id="TEST_ASSET")

    print("🔌 Connecting to WX...")

    # Debug: check where Playwright expects Chromium
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        chromium_path = pw.chromium.executable_path
        print(f"📂 Playwright Chromium executable path: {chromium_path}")

    # Now actually connect
    await wx.connect()

    print("✅ Connected. Listing orders...")
    orders = await wx.list_open_orders()
    print("Orders:", orders)

    await wx.close()

if __name__ == "__main__":
    asyncio.run(main())
