# Delay-EaseV3

An automated delay repay system for UK train operators that processes ticket images, calculates delay compensation, and submits claims automatically.

## Overview

Delay-EaseV2 streamlines the delay repay process by extracting ticket information from images, checking for delays using real-time data, and automating claim submissions through train operator websites. The system supports Type A train operating companies including CrossCountry, Transport for Wales, TransPennine Express, Great Western Railway, Northern, and South Western Railway.

## Main Scripts

### `delay_ease_main.py`
The primary entry point that orchestrates the complete workflow. Processes a ticket image through extraction, delay verification, and automated submission. Handles both command-line usage and test scenarios. Manages user details and bank information for form completion.

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

## Setup

1. Copy `env_example.txt` to `.env` and configure your credentials
2. Install dependencies: `poetry install`
3. Run with a ticket image: `python delay_ease_main.py path/to/ticket.png`

## Requirements

- OpenAI API access for ticket extraction
- HSP API credentials for delay verification  
- Delay repay website login credentials
- UK train ticket images (e-tickets or m-tickets)

The system currently supports automated claims for Etickets and Type A operators with plans to expand coverage to additional train companies.
