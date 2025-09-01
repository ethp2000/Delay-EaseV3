## Delay-EaseV3

Delay-Ease takes a UK train ticket screenshot, checks if you’re eligible for Delay Repay, and, if eligible, can auto-fill and submit a claim for supported operators.

## Overview
Delay-EaseV3 streamlines the delay repay process by extracting ticket information from images, checking for delays using real-time data, and (when 
eligible) automating claim submissions through train operator websites. The system supports Type A train operating companies including CrossCountry, 
Transport for Wales, TransPennine Express, Great Western Railway, Northern, and South Western Railway.

## Quickstart

```bash
poetry install && poetry run playwright install chromium
cp env_example.txt .env
poetry run python main.py data/test_tickets/eticket_test2.png
```

## Requirements
- Python 3.11+
- Poetry
- OpenAI API key
- HSP credentials (for delay verification)
- Playwright Chromium (for browser automation via `browser-use`) 

## Environment
Edit `.env` (copied from `env_example.txt`):
- Minimum to extract + check delay:
  - OPENAI_API_KEY
  - HSP_EMAIL, HSP_PASSWORD
- Needed for automated claim submission:
  - DELAY_REPAY_EMAIL, DELAY_REPAY_PASSWORD
  - USER_* (title, name, address, email, bank account holder/sort code/account)


