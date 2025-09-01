## Delay-EaseV3

Delay-Ease takes a UK train ticket screenshot, checks if you’re eligible for Delay Repay, and, if eligible, can auto-fill and submit a claim for supported operators.

## Overview
Delay-EaseV3 streamlines the delay repay process by extracting ticket information from images, checking for delays using real-time data, and (when 
eligible) automating claim submissions through train operator websites. The system supports Type A train operating companies including CrossCountry, 
Transport for Wales, TransPennine Express, Great Western Railway, Northern, and South Western Railway.

### Quickstart 
```bash
poetry install && poetry run playwright install chromium
cp env_example.txt .env   
poetry run python main.py --image data/test_tickets/eticket_test2.png
```

## Requirements
- Python 3.11+
- Poetry
- OpenAI API key
- HSP credentials (for delay verification)
- Playwright Chromium (for browser automation via `browser-use`) 

Needed for automated claim submission (Type A):
- `DELAY_REPAY_EMAIL`, `DELAY_REPAY_PASSWORD`
- `USER_TITLE`, `USER_FIRST_NAME`, `USER_LAST_NAME`, `USER_ADDRESS`, `USER_CITY`, `USER_POSTCODE`, `USER_COUNTRY`, `USER_EMAIL`
- `USER_ACCOUNT_HOLDER`, `USER_SORT_CODE`, `USER_ACCOUNT_NUMBER`

### CLI usage
- Run with a specific image:
```bash
poetry run python main.py --image path/to/your_ticket.png --user-id my_user
```

- Run the built‑in test (uses `data/test_tickets/eticket_test1.png`):
```bash
poetry run python main.py
```

- Help:
```bash
poetry run python main.py --help
```

### Notes and limitations
- Focused on UK e‑tickets. Paper tickets are detected and rejected.
- HSP API and operator websites can change; automation may need updates over time.

### Dev
- Lint and format:
```bash
make format
make lint
```

### How it works (high level)
- Ticket parsing (vision): `src/delay_ease/ticket_data_extraction.py`
  - Uses OpenAI Vision to read an e‑ticket image and extract: date, departure/arrival stations, times, format, etc.
  - Validates against `data/reference_data/stations.csv` to align station names and CRS codes.
- Delay lookup (HSP): `src/delay_ease/delay_calculation.py`
  - Authenticates with the UK Rail Historical Service Performance (HSP) API.
  - Finds the train by scheduled departure time and compares scheduled vs actual arrival to calculate delay minutes.
  - Maps the TOC code to the operator name using `data/reference_data/toc_code.csv`.
- Eligibility + compensation
  - Uses `data/reference_data/delay_repay_percentages_single_tickets.csv` to determine the compensation bracket per operator.
  - Returns a status message explaining eligibility and next steps.
- Optional auto‑claim (Type A TOCs): `src/delay_ease/browser_automation_type_a.py`
  - Automates browser steps with `browser-use` Agents to log in, enter journey details, upload the ticket, and review.
  - Currently targeted at “Type A” operators (CrossCountry, TfW, TPE, GWR, Northern, SWR). Real sites change—expect brittleness.
- Persistence
  - Writes run results to `data/results/delay_ease_result_YYYYMMDD_HHMMSS.json`.
  - Stores claim records in `data/claims/DE_YYYYMMDD_HHMMSS_<user>.json`.