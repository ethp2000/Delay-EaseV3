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
poetry run python src/delay_ease/main.py data/test_tickets/eticket_test2.png
```

## Requirements
- Python 3.11+
- Poetry
- OpenAI API key
- HSP credentials (for delay verification)
- Playwright Chromium (for browser automation via `browser-use`) [[memory:7739255]]

## Environment
Edit `.env` (copied from `env_example.txt`):
- Minimum to extract + check delay:
  - OPENAI_API_KEY
  - HSP_EMAIL, HSP_PASSWORD
- Needed for automated claim submission:
  - DELAY_REPAY_EMAIL, DELAY_REPAY_PASSWORD
  - USER_* (title, name, address, email, bank account holder/sort code/account)

## Usage

- Run the main function with a ticket image:
```bash
poetry run python src/delay_ease/main.py data/test_tickets/eticket_test1.png
```

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
