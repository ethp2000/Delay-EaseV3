import asyncio
import datetime
import json
import logging
import os
from pathlib import Path

from src.delay_ease.browser_automation_type_a import run_type_a_automation
from src.delay_ease.delay_calculation import calculate_delay_compensation
from src.delay_ease.utils import is_type_a_toc

log = logging.getLogger(__name__)


def get_user_details():
    """Get user details with fail-fast validation for required fields"""
    required_user_vars = [
        "USER_TITLE",
        "USER_FIRST_NAME",
        "USER_LAST_NAME",
        "USER_ADDRESS",
        "USER_CITY",
        "USER_POSTCODE",
        "USER_COUNTRY",
        "USER_EMAIL",
        "USER_ACCOUNT_HOLDER",
        "USER_SORT_CODE",
        "USER_ACCOUNT_NUMBER",
    ]

    missing_vars = [var for var in required_user_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    p = {
        "title": os.environ["USER_TITLE"],
        "first_name": os.environ["USER_FIRST_NAME"],
        "last_name": os.environ["USER_LAST_NAME"],
        "address_line1": os.environ["USER_ADDRESS"],
        "town_city": os.environ["USER_CITY"],
        "postcode": os.environ["USER_POSTCODE"],
        "country": os.environ["USER_COUNTRY"],
        "email": os.environ["USER_EMAIL"],
    }
    b = {
        "account_holder": os.environ["USER_ACCOUNT_HOLDER"],
        "sort_code": os.environ["USER_SORT_CODE"],
        "account_number": os.environ["USER_ACCOUNT_NUMBER"],
    }
    return {"passenger": p, "bank": b}


def save_claim_record(
    user_id: str, ticket_data: dict, claim_reference: str = None
) -> str:
    claims_dir = Path("data/claims")
    claims_dir.mkdir(exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    claim_id = f"DE_{timestamp}_{user_id}"

    claim_record = {
        "claim_id": claim_id,
        "user_id": user_id,
        "toc_claim_reference": claim_reference,
        "status": ticket_data.get("status", "unknown"),
        "toc": ticket_data.get("train_operator", "Unknown"),
        "journey_date": ticket_data.get("ticket_date", "Unknown"),
        "departure_station": ticket_data.get("departure_station", "Unknown"),
        "arrival_station": ticket_data.get("arrival_station", "Unknown"),
        "delay_minutes": ticket_data.get("delay_minutes", 0),
        "compensation_percentage": ticket_data.get("compensation_percentage", "0%"),
        "compensation_amount": ticket_data.get("compensation_amount"),
        "submitted_at": datetime.datetime.now().isoformat(),
        "ticket_image_path": ticket_data.get("image_path", ""),
    }

    claim_file = claims_dir / f"{claim_id}.json"
    with open(claim_file, "w") as f:
        json.dump(claim_record, f, indent=2)

    return claim_id


def display_status_message(ticket_data: dict):
    """Display user-friendly status messages with appropriate emojis and formatting"""
    status = ticket_data.get("status", "unknown")
    message = ticket_data.get("message", "Unknown status")

    if status == "blocked_paper":
        log.warning("PAPER TICKET DETECTED")

    elif status.startswith("ineligible"):
        log.info("NOT ELIGIBLE FOR COMPENSATION")

        if "learn_more" in ticket_data.get("next_action", ""):
            log.info(
                f"Learn more about {ticket_data.get('learn_more_topic', 'delay repay policies')}"
            )

    elif status == "eligible":
        compensation = ticket_data.get("compensation_percentage", "Unknown")
        delay = ticket_data.get("delay_minutes", 0)
        toc = ticket_data.get("train_operator", "Unknown")
        dep_station = ticket_data.get("departure_station", "Unknown")
        arr_station = ticket_data.get("arrival_station", "Unknown")
        dep_time = ticket_data.get("departure_time", "Unknown")
        journey_date = ticket_data.get("ticket_date", "Unknown")

        log.info("ELIGIBLE FOR COMPENSATION!")
        log.info("=" * 60)
        log.info(f"{message}")
        log.info("Details:")
        log.info(f"   Operator: {toc}")
        log.info(f"   From: {dep_station}")
        log.info(f"   To: {arr_station}")
        log.info(f"   Date: {journey_date}")
        log.info(f"   Departure time: {dep_time}")
        log.info(f"   Delay: {delay} minutes")
        log.info(f"   Compensation: {compensation}")

        amount = ticket_data.get("compensation_amount")
        if amount:
            log.info(f"   Estimated amount: £{amount:.2f}")

    elif status.startswith("error"):
        log.error("ERROR PROCESSING TICKET")
        log.error(f"{message}")

    else:
        log.info(f"STATUS: {status.upper()}")
        log.info(f"{message}")


def process_single_ticket(image_path: str, user_id: str = "test_user") -> dict:
    log.info("DELAY EASE - AUTOMATED DELAY REPAY")
    log.info(f"Processing ticket: {os.path.basename(image_path)}")

    if not os.path.exists(image_path):
        return {
            "status": "error_file_not_found",
            "message": f"Ticket file not found: {image_path}",
            "next_action": "upload_valid_file",
        }

    try:
        # phase 1 & 2: extract ticket data and check eligibility
        log.info("Analyzing ticket and checking for delays...")
        ticket_data = calculate_delay_compensation(image_path)
        ticket_data["image_path"] = os.path.abspath(image_path)

        display_status_message(ticket_data)

        # phase 3: proceed with automation if eligible
        if ticket_data.get("status") == "eligible":
            toc = ticket_data.get("train_operator", "")

            if is_type_a_toc(toc):
                log.info(f"Proceeding with automated claim submission for {toc}...")

                journey_details = {
                    "train_operator": toc,
                    "date": ticket_data.get("ticket_date", ""),
                    "departure_time": ticket_data.get("departure_time", ""),
                    "departure_station": ticket_data.get("departure_station", ""),
                    "arrival_station": ticket_data.get("arrival_station", ""),
                    "delay_minutes": ticket_data.get("delay_minutes", 0),
                }

                user_details = get_user_details()

                # phase 4: run automation
                try:
                    log.info("Submitting claim automatically...")
                    asyncio.run(
                        run_type_a_automation(
                            journey_details,
                            user_details["passenger"],
                            user_details["bank"],
                            ticket_data["image_path"],
                        )
                    )

                    # phase 5: store claim record
                    claim_id = save_claim_record(user_id, ticket_data, "AUTO_SUBMITTED")

                    log.info("CLAIM SUBMITTED SUCCESSFULLY!")
                    log.info(f"Claim ID: {claim_id}")
                    log.info(
                        "You will receive a notification when compensation is ready for withdrawal"
                    )

                    ticket_data["claim_id"] = claim_id
                    ticket_data["automation_status"] = "submitted"

                except Exception as e:
                    log.error(f"Error during automation: {e}")
                    ticket_data["automation_status"] = "failed"
                    ticket_data["automation_error"] = str(e)

            else:
                log.info(f"{toc} automation not yet available")
                log.info("Your claim details have been saved for manual processing")

                claim_id = save_claim_record(user_id, ticket_data, "MANUAL_REQUIRED")
                ticket_data["claim_id"] = claim_id
                ticket_data["automation_status"] = "manual_required"

        elif ticket_data.get("status", "").startswith("ineligible"):
            claim_id = save_claim_record(user_id, ticket_data, "INELIGIBLE")
            ticket_data["claim_id"] = claim_id

        log.info("=" * 60)
        return ticket_data

    except Exception as e:
        log.error(f"Unexpected error processing ticket: {e}")
        error_data = {
            "status": "error_processing",
            "message": f"Unexpected error: {str(e)}",
            "next_action": "contact_support",
        }
        display_status_message(error_data)
        return error_data
