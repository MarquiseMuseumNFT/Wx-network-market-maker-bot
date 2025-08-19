import asyncio
import logging
import signal
from config import settings
from grid import build_grid, total_notional, diff_books
from exchanges.htx import HTXMarketData
from exchanges.wx import WXExchange

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("grid-bot")

STOP = asyncio.Event()

def handle_stop(*_):
    log.info("Shutdown signal received; stopping...")
    STOP.set()

async def run():
    md = HTXMarketData(symbol=settings.ref_symbol)
    wx = WXExchange(
        target_asset_id=settings.target_asset_id,
        seed=settings.wx_seed,
        private_key=settings.wx_private_key,
        public_key=settings.wx_public_key,
        wallet=settings.wx_wallet,
        login_pass=settings.wx_login_pass,
    )

    await wx.connect()
    await md.connect()
    log.info("Connected to adapters (WX + HTX).")

    last_mid = None  # cache last known mid price

    try:
        while not STOP.is_set():
            try:
                mid = await md.mid_price()
            except Exception as e:
                log.error(f"Error fetching HTX price: {e}")
                mid = None

            if mid is None:
                if last_mid is not None:
                    log.warning("HTX feed failed; reusing last known mid price.")
                    mid = last_mid
                else:
                    log.warning("No mid price yet; retrying...")
                    await asyncio.sleep(1)
                    continue
            else:
                last_mid = mid  # update cache

            # Build grid from mid
            grid = build_grid(mid, settings.grid_levels, settings.grid_spacing_bps, settings.order_size)
            notion = total_notional(grid)
            if notion > settings.max_notional:
                log.warning(f"Grid notional {notion:.2f} exceeds MAX_NOTIONAL {settings.max_notional}; shrinking sizes.")
                scale = settings.max_notional / max(notion, 1e-9)
                for g in grid:
                    g.size *= scale

            # Diff current vs target orders
            current = await wx.list_open_orders()
            cancels, creates = diff_books(current, grid)

            if cancels:
                log.info(f"Cancelling {len(cancels)} stale orders...")
                await wx.cancel_orders(cancels)

            if creates:
                log.info(f"Placing {len(creates)} grid orders...")
                await wx.place_orders(creates)

            await asyncio.sleep(settings.refresh_seconds)

    finally:
        if settings.cancel_on_exit:
            try:
                log.info("Cancelling all orders on exit...")
                await wx.cancel_all()
            except Exception as e:
                log.error(f"Error during cancel_all: {e}")
        await md.close()
        await wx.close()
        log.info("Shutdown complete.")

if __name__ == "__main__":
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_stop)
    asyncio.run(run())
