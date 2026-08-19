# Stock Portfolio Monitor Bot

Telegram bot for manually tracked Vietnamese stock positions. It does NOT place orders.

Flow:
- User creates a position: symbol, quantity, entry, purchase time, note.
- User presses FOLLOW.
- Bot runs at end of trading session and produces a report.
- News is organized into market-wide, sector, and company levels so multiple holdings do not mix blindly.
- AI receives market data + news and returns a reasoned assessment.

IMPORTANT: FireAnt and market-data integrations are adapters. Do not scrape or bypass access controls. Connect only to an API/feed you are authorized to use.
