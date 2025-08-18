# WX Grid Bot

A modernized Python grid trading bot for [WX.Network](https://wx.network).

## Features
- Uses WX Matcher REST API (no CCXT)
- Safe `.env`-based secret management
- Grid strategy with configurable levels & spacing
- Dry-run mode for testing

## Quickstart
```bash
git clone https://github.com/YOURNAME/wx-grid-bot.git
cd wx-grid-bot
cp .env.example .env
pip install -r requirements.txt
bash start.sh
```

Secrets (`WAVES_SEED`) are **never committed**. They live in `.env` (ignored by git) or in your hosting provider’s environment variables.
