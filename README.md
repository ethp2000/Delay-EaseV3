# Delay-EaseV3

An automated delay repay system for UK train operators that processes ticket images, calculates delay compensation, and submits claims automatically.

## Overview

Delay-EaseV3 streamlines the delay repay process by extracting ticket information from images, checking for delays using real-time data, and (when eligible) automating claim submissions through train operator websites. The system supports Type A train operating companies including CrossCountry, Transport for Wales, TransPennine Express, Great Western Railway, Northern, and South Western Railway.

## Getting Started

- Requirements
  - Python 3.11+
  - Poetry
  - OpenAI API access (model `gpt-4.1`)
  - HSP API credentials (for delay verification)
  - Delay Repay portal credentials (for automation)
  - Playwright Chromium browser installed (used by the automation layer)

- Install
```bash
cd /Users/ethanphillips/Desktop/Delay-EaseV3
poetry install
poetry run playwright install chromium
```

- Environment
```bash
cp env_example.txt .env
# Then edit .env and set at least:
OPENAI_API_KEY=...
# optional:
OPENAI_ORGANIZATION=...
OPENAI_PROJECT=...
# HSP API (required for delay verification)
HSP_EMAIL=...
HSP_PASSWORD=...
# Delay Repay login (required for automation)
DELAY_REPAY_EMAIL=...
DELAY_REPAY_PASSWORD=...
# Passenger + bank details (required for automation)
USER_TITLE=Mr/Ms
USER_FIRST_NAME=...
USER_LAST_NAME=...
USER_ADDRESS=...
USER_CITY=...
USER_POSTCODE=...
USER_COUNTRY=UK
USER_EMAIL=...
USER_ACCOUNT_HOLDER=...
USER_SORT_CODE=00-00-00
USER_ACCOUNT_NUMBER=00000000
```

## Usage

- Run with a ticket image
```bash
poetry run python src/delay_ease/main.py data/test_tickets/eticket_test1.png
```

- Run with a ticket image and custom user id
```bash
poetry run python src/delay_ease/main.py data/test_tickets/eticket_test1.png my_user_123
```

- Built-in test mode (uses a sample test ticket)
```bash
poetry run python src/delay_ease/main.py
# or
poetry run python src/delay_ease/main.py test
```

Outputs are saved to `data/results/` and claim records to `data/claims/`.

## Notes

- Paper tickets are currently blocked; use e-tickets or m-tickets.
- Supported Type A operators: CrossCountry, Transport for Wales, TransPennine Express, Great Western Railway, Northern, South Western Railway (incl. Island Line).
- Automation uses `browser-use` with Playwright Chromium; ensure the browser install step above has been run.

## Main Scripts

### `main.py`
Primary entry point. Processes a ticket image through extraction, delay verification, and automated submission. Handles both command-line usage and test scenarios. Manages user details and bank information for form completion.

### `browser_automation_type_a.py`
Handles automated web browser interactions for Type A train operators. Uses browser-use library to navigate delay repay websites, log in with credentials, fill forms, upload ticket images, and complete claims. Includes file upload capabilities and error handling for web automation.

### `ticket_data_extraction.py`
Extracts ticket information from images using OpenAI's Vision API. Identifies ticket format (paper vs digital), parses journey details including stations, times, and dates. Validates station codes against the UK rail network database and handles both single and multi-segment journeys.

### `delay_calculation.py`
Determines delay eligibility and compensation amounts. Connects to Historical Service Performance (HSP) API to retrieve actual train performance data. Calculates delay minutes, checks against 28-day claim windows, and determines compensation percentages based on operator policies.

### `const.py`
Configuration file containing supported train operators, their delay repay website URLs, and allowed domains for browser automation. Defines the mapping between operator names and their respective claim portals.

### `utils.py`
Helper functions for operator validation and website URL retrieval. Provides utilities to check if a train operator supports Type A automation and returns the appropriate delay repay website.

## Builder Modules

### `builders/prompt_builder.py`
Generates dynamic prompts for different automation stages. Creates context-aware instructions for login procedures, journey details entry, ticket uploads, and final review processes. Customizes prompts based on operator websites and user data.

### `builders/func_builder.py`
Constructs JavaScript functions for browser automation. Builds file input manipulation code and other browser-specific utilities required for web form interactions.

The system currently supports automated claims for e-tickets and Type A operators, with plans to expand coverage to additional train companies.
