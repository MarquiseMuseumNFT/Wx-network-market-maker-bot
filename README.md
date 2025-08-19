# Grid Market-Making Bot — Starter (Safe Skeleton)

**Important security note:** You pasted highly sensitive secrets (seed phrase, private key, login password).
Do **not** share those with anyone. Treat them as compromised and **rotate them immediately**:

- Generate a brand-new wallet and transfer any funds.
- Revoke/rotate API keys and passwords.
- Never hardcode secrets in code or commit them to Git.
- Store them as environment variables (Render dashboard → Environment).

This starter gives you a clean structure without embedding any secrets. You must fill in the specific API
endpoints and signing details for both WX Network (trading) and HTX (market data) using their official docs.
Until you do, this app will run but not place any real orders.

## What it does
- Connects to a reference market feed (e.g., HTX `waves_usdt`) to get a mid-price.
- Builds a 10×10 grid (10 orders on each side) around that mid-price.
- Places/cancels/refreshes orders on WX for a target market (the unlisted pair you provided).
- Includes guardrails: max notional, cancel on shutdown, basic retry/backoff.

## What you must do before deployment
1. **Rotate your leaked credentials** and create new ones. Use a new wallet.
2. Fill the TODOs in `exchanges/htx.py` and `exchanges/wx.py`:
   - WebSocket/REST endpoints
   - Auth/signing logic
   - Symbol/pair formatting
3. Set environment variables in Render (or locally with a `.env` file):

   ```env
   # General
   BOT_ENV=prod                   # or 'dev'
   LOG_LEVEL=INFO
   REF_SYMBOL=WAVES_USDT          # reference market on HTX (example)
   TARGET_ASSET_ID=<WX_ASSET_ID>  # your WX target asset ID/pair key
   GRID_LEVELS=10
   GRID_SPACING_BPS=50            # 50 = 0.50% spacing (example; tune as needed)
   ORDER_SIZE=5                   # base size per order (units of TARGET asset or quote; see WX adapter)
   MAX_NOTIONAL=500               # cap total outstanding notional (quote currency units)
   REFRESH_SECONDS=15             # how often to re-sync grid
   CANCEL_ON_EXIT=true

   # Secrets (DO NOT COMMIT; set only in Render dashboard)
   WX_SEED=
   WX_PRIVATE_KEY=
   WX_PUBLIC_KEY=
   WX_WALLET=
   WX_LOGIN_PASS=
   ```

4. **Test in a paper/sandbox** first if available. If not, limit size, frequency, and set tight `MAX_NOTIONAL`.
5. Deploy using the provided `render.yaml` as a **Background Worker**.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Render deployment
- Push this repo to GitHub
- Create a **Background Worker** on Render and point it at your repo
- Use `render.yaml` here for defaults, or configure manually
- Set all required environment variables in Render **before** starting

## Legal & risk disclosures
- Market making on illiquid/unlisted pairs can be extremely volatile. You can lose 100% of capital.
- Grid strategies can accumulate inventory and adverse selection in trends.
- You are solely responsible for complying with local laws and exchange terms.
- This code is for educational purposes; no warranty or financial advice provided.