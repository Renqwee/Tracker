# Tracker

A Telegram bot that monitors product prices and alerts you when they change.

## Features

- Add product URLs to track
- Get notified when prices drop, hit a target, or change at all
- View and manage your tracked products
- Checks prices every hour automatically

## Setup

1. Clone the repo
2. Install dependencies:
```bash
   pip install -r requirements.txt
```
3. Fill in `config.py` with your credentials:
   - Telegram bot token (from BotFather)
   - PostgreSQL connection details
4. Run:
```bash
   python main.py
```

## Supported Sites

| Site | Country |
|------|---------|
| Amazon |  SA |
| Noon |  SA |
| Carrefour |  SA |
| Extra |  SA |
| AliExpress |  Global |

## Stack

Python · PostgreSQL · python-telegram-bot · APScheduler

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
