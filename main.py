import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv

from src.delay_ease.service import process_single_ticket

load_dotenv()


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
    )


setup_logging()

log = logging.getLogger(__name__)
app = typer.Typer()


@app.command()
def run(
    image: Optional[Path] = typer.Option(None, help="Path to ticket image (.png/.jpg)"),
    user_id: str = typer.Option("test_user", help="Optional user id for saved records"),
):
    """Run Delay-Ease on a ticket image. If --image is omitted, runs a built-in test."""
    if image is None:
        test_eticket_test()
        return

    result = process_single_ticket(str(image), user_id)
    log.info(" RESULTS SUMMARY")
    log.info(f"Status: {result.get('status', 'Unknown')}")
    log.info(f"TOC: {result.get('train_operator', 'Unknown')}")
    log.info(f"Delay: {result.get('delay_minutes', 'Unknown')} minutes")
    log.info(f"Compensation: {result.get('compensation_percentage', 'Unknown')}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"data/results/delay_ease_result_{timestamp}.json"
    os.makedirs("data/results", exist_ok=True)

    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    log.info(f"Full result saved to: {result_file}")


def test_eticket_test():

    TEST_TICKET_FILE = "eticket_test1.png"

    log.info(f"TESTING DELAY EASE WITH {TEST_TICKET_FILE}")

    test_image_path = f"data/test_tickets/{TEST_TICKET_FILE}"
    test_user_id = f"test_user_{TEST_TICKET_FILE.replace('.png', '')}"

    result = process_single_ticket(test_image_path, test_user_id)

    log.info("TEST RESULTS SUMMARY")
    log.info(f"Tested: {TEST_TICKET_FILE}")
    log.info(f"Status: {result.get('status', 'Unknown')}")
    log.info(f"TOC: {result.get('train_operator', 'Unknown')}")
    log.info(f"Delay: {result.get('delay_minutes', 'Unknown')} minutes")
    log.info(f"Compensation: {result.get('compensation_percentage', 'Unknown')}")

    return result


if __name__ == "__main__":
    app()
