import asyncio
import logging
import os

from browser_use import ActionResult, Agent, Browser, ChatOpenAI, Controller

from src.delay_ease.builders.func_builder import build_file_input_js
from src.delay_ease.builders.prompt_builder import (
    build_journey_details_prompt,
    build_login_prompt,
    build_review_prompt,
    build_ticket_details_prompt,
)
from src.delay_ease.const import ALLOWED_DOMAINS
from src.delay_ease.ticket_data_extraction import extract_ticket_details
from src.delay_ease.utils import get_operator_website

log = logging.getLogger(__name__)


def get_delay_repay_credentials():
    email = os.environ.get("DELAY_REPAY_EMAIL")
    password = os.environ.get("DELAY_REPAY_PASSWORD")

    if not email or not password:
        raise ValueError(
            "Missing required environment variables: DELAY_REPAY_EMAIL, DELAY_REPAY_PASSWORD"
        )

    return email, password


def validate_ticket_file(ticket_image_path: str) -> bool:
    try:
        abs_path = os.path.abspath(ticket_image_path)
        if not os.path.exists(abs_path):
            log.error(f"Ticket file does not exist: {abs_path}")
            return False

        file_size = os.path.getsize(abs_path)
        if file_size == 0:
            log.error(f"Ticket file is empty: {abs_path}")
            return False

        log.info(f"Ticket file validated: {abs_path} ({file_size} bytes)")
        return True

    except Exception as e:
        log.error(f"Error validating ticket file: {str(e)}")
        return False


def validate_ticket_matches_journey(
    ticket_image_path: str, journey_details: dict
) -> bool:
    """
    CRITICAL SECURITY: Validate that the uploaded ticket matches the journey being claimed.
    This prevents fraudulent claims using wrong tickets as proof.
    """
    try:
        extracted_data = extract_ticket_details(ticket_image_path)

        if "error" in extracted_data:
            log.warning(
                f"SECURITY WARNING: Could not validate ticket - {extracted_data['error']}"
            )
            return False

        ticket_data = (
            extracted_data["segments"][0]
            if "segments" in extracted_data
            else extracted_data
        )

        journey_date = journey_details["date"]
        departure_station = journey_details["departure_station"]
        arrival_station = journey_details["arrival_station"]

        ticket_date = ticket_data.get("ticket_date", "")
        ticket_departure = ticket_data.get("departure_station", "")
        ticket_arrival = ticket_data.get("arrival_station", "")

        date_match = journey_date in ticket_date or ticket_date in journey_date
        departure_match = (
            departure_station.lower() in ticket_departure.lower()
            or ticket_departure.lower() in departure_station.lower()
        )
        arrival_match = (
            arrival_station.lower() in ticket_arrival.lower()
            or ticket_arrival.lower() in arrival_station.lower()
        )

        if not (date_match and departure_match and arrival_match):
            log.warning("SECURITY BLOCK: Ticket details don't match journey")
            log.warning(
                f"Journey: {journey_date}, {departure_station} → {arrival_station}"
            )
            log.warning(
                f"Ticket:  {ticket_date}, {ticket_departure} → {ticket_arrival}"
            )
            return False

        log.info("Ticket matches journey details")
        return True

    except Exception as e:
        log.warning(f"SECURITY WARNING: Error validating ticket match - {str(e)}")
        return False


async def create_browser():
    browser = Browser(
        headless=False,
        user_data_dir=None,
        window_size={"width": 1280, "height": 1080},
        allowed_domains=ALLOWED_DOMAINS,
        keep_alive=True,
    )
    return browser


async def create_controller():
    """Create controller with file upload capability for ticket uploads"""

    controller = Controller()

    @controller.action("Upload ticket")
    async def upload_ticket(file_path: str, page):
        try:
            if not file_path:
                log.error("Error: Empty file path provided")
                return ActionResult(extracted_content="Failed: Empty file path")

            abs_path = os.path.abspath(file_path)
            log.info(f"Attempting to upload file: {abs_path}")

            if not os.path.exists(abs_path):
                log.error(f"Error: File does not exist at path: {abs_path}")
                return ActionResult(
                    extracted_content=f"Failed: File not found at {abs_path}"
                )

            log.info(f"File exists and has size: {os.path.getsize(abs_path)} bytes")

            result = await page.evaluate(build_file_input_js())
            if result:
                log.info("Made file input visible with JavaScript")
                file_input = await page.wait_for_selector(
                    'input[type="file"]', timeout=5000
                )

                if file_input:
                    log.info(f"Found file input, setting file: {abs_path}")
                    await file_input.set_input_files(abs_path)
                    log.info("Successfully set input files")

                    # Brief pause to allow upload to process - EXACT OpenAI timing
                    await asyncio.sleep(2)

                    return ActionResult(
                        extracted_content=f"Upload successful: {os.path.basename(abs_path)}",
                        include_in_memory=True,
                    )
                else:
                    log.error(
                        "Error: Could not find file input element even after making it visible"
                    )
                    return ActionResult(
                        extracted_content="Failed: Could not find file input element"
                    )
            else:
                log.error("Error: No file input elements found on page")
                return ActionResult(
                    extracted_content="Failed: No file input elements found"
                )

        except Exception as e:
            log.error(f"Unexpected error in upload_ticket: {str(e)}")
            return ActionResult(extracted_content=f"Failed to upload ticket: {str(e)}")

    return controller


async def run_type_a_automation(
    journey_details: dict,
    passenger_details: dict,
    bank_details: dict,
    ticket_image_path: str,
):

    browser = await create_browser()

    try:
        llm = ChatOpenAI(
            model="o3",
        )
        # browser use update mean no controler needed, but may be needed for future versions
        # controller = await create_controller()
        # log.info("Controller created for file uploads")

        # Get credentials with validation
        delay_repay_email, delay_repay_password = get_delay_repay_credentials()

        operator_website = get_operator_website(journey_details["train_operator"])

        login_agent = Agent(
            task=build_login_prompt(
                operator_website, delay_repay_email, delay_repay_password
            ),
            llm=llm,
            browser=browser,
            use_vision=False,
        )

        await login_agent.run()
        log.info("Login completed")

        journey_date = journey_details["date"]
        departure_time = journey_details["departure_time"]
        departure_station = journey_details["departure_station"]
        arrival_station = journey_details["arrival_station"]
        delay_minutes = journey_details["delay_minutes"]

        # Calculate the appropriate delay range for Type A TOCs (standardized ranges)
        if delay_minutes < 30:
            delay_range = "15-29 minutes"
        elif delay_minutes < 60:
            delay_range = "30-59 minutes"
        elif delay_minutes < 120:
            delay_range = "60-119 minutes"
        else:
            delay_range = "120+ minutes"

        log.info(f"Delay: {delay_minutes} minutes → Looking for range: {delay_range}")

        journey_agent = Agent(
            task=build_journey_details_prompt(
                journey_date,
                departure_station,
                arrival_station,
                departure_time,
                delay_range,
                delay_minutes,
            ),
            llm=llm,
            browser=browser,
            use_vision=True,
        )

        await journey_agent.run()
        log.info("Journey details entered")

        log.info("Starting ticket selection and upload...")
        ticket_agent = Agent(
            task=build_ticket_details_prompt(ticket_image_path),
            llm=llm,
            browser=browser,
            use_vision=True,
            directly_open_url=False,
            available_file_paths=[ticket_image_path],
        )

        ticket_result = await ticket_agent.run()
        log.info(f"Ticket upload completed: {ticket_result}")

        log.info("Starting final review...")
        review_agent = Agent(
            task=build_review_prompt(
                passenger_details,
                bank_details,
                departure_station,
                arrival_station,
                journey_date,
                departure_time,
                delay_minutes,
            ),
            llm=llm,
            browser=browser,
            use_vision=True,
        )

        review_result = await review_agent.run()
        log.info(f"Review completed: {review_result}")

    finally:
        if browser:
            await browser.close()
            log.info("Browser session closed")
