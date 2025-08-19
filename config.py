import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    bot_env: str = Field(default=os.getenv("BOT_ENV", "dev"))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))

    ref_symbol: str = Field(default=os.getenv("REF_SYMBOL", "WAVES-USDT"))
    target_asset_id: str = Field(default=os.getenv("TARGET_ASSET_ID", ""))  # WX pair/asset id

    grid_levels: int = Field(default=int(os.getenv("GRID_LEVELS", "10")))
    grid_spacing_bps: float = Field(default=float(os.getenv("GRID_SPACING_BPS", "50")))
    order_size: float = Field(default=float(os.getenv("ORDER_SIZE", "5")))
    max_notional: float = Field(default=float(os.getenv("MAX_NOTIONAL", "500")))
    refresh_seconds: int = Field(default=int(os.getenv("REFRESH_SECONDS", "15")))
    cancel_on_exit: bool = Field(default=os.getenv("CANCEL_ON_EXIT", "true").lower() == "true")

    # Secrets (Render dashboard only)
    wx_seed: str = Field(default=os.getenv("WX_SEED", ""))
    wx_private_key: str = Field(default=os.getenv("WX_PRIVATE_KEY", ""))
    wx_public_key: str = Field(default=os.getenv("WX_PUBLIC_KEY", ""))
    wx_wallet: str = Field(default=os.getenv("WX_WALLET", ""))
    wx_login_pass: str = Field(default=os.getenv("WX_LOGIN_PASS", ""))

settings = Settings()
