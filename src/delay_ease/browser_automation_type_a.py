import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from browser_use import Agent, BrowserSession
from browser_use.llm import ChatOpenAI
from delay_calculation import Delay_calc
from ticket_data_extraction import extract_ticket_details, get_data_path
from const import TYPE_A_TOCS, ALLOWED_DOMAINS
from utils import is_type_a_toc, get_operator_website
from builders.func_builder import build_file_input_js
from builders.prompt_builder import build_login_prompt, build_journey_details_prompt, build_ticket_details_prompt, build_review_prompt

load_dotenv()



DELAY_REPAY_EMAIL = os.environ.get("DELAY_REPAY_EMAIL")
DELAY_REPAY_PASSWORD = os.environ.get("DELAY_REPAY_PASSWORD")

if not DELAY_REPAY_EMAIL or not DELAY_REPAY_PASSWORD:
    raise ValueError("Missing required environment variables: DELAY_REPAY_EMAIL, DELAY_REPAY_PASSWORD")

def validate_ticket_file(ticket_image_path: str) -> bool:
    try:
        abs_path = os.path.abspath(ticket_image_path)
        if not os.path.exists(abs_path):
            print(f"Ticket file does not exist: {abs_path}")
            return False
        
        file_size = os.path.getsize(abs_path)
        if file_size == 0:
            print(f"Ticket file is empty: {abs_path}")
            return False
            
        print(f"Ticket file validated: {abs_path} ({file_size} bytes)")
        return True
        
    except Exception as e:
        print(f"Error validating ticket file: {str(e)}")
        return False

def validate_ticket_matches_journey(ticket_image_path: str, journey_details: dict) -> bool:
    """
    CRITICAL SECURITY: Validate that the uploaded ticket matches the journey being claimed.
    This prevents fraudulent claims using wrong tickets as proof.
    """
    try:   
        extracted_data = extract_ticket_details(ticket_image_path)
        
        if "error" in extracted_data:
            print(f" SECURITY WARNING: Could not validate ticket - {extracted_data['error']}")
            return False
        
        ticket_data = extracted_data["segments"][0] if "segments" in extracted_data else extracted_data
    
        journey_date = journey_details["date"]
        departure_station = journey_details["departure_station"]
        arrival_station = journey_details["arrival_station"]
        departure_time = journey_details["departure_time"]
        
        ticket_date = ticket_data.get("ticket_date", "")
        ticket_departure = ticket_data.get("departure_station", "")
        ticket_arrival = ticket_data.get("arrival_station", "")
        ticket_time = ticket_data.get("departure_time", "")
        
        date_match = journey_date in ticket_date or ticket_date in journey_date
        departure_match = departure_station.lower() in ticket_departure.lower() or ticket_departure.lower() in departure_station.lower()
        arrival_match = arrival_station.lower() in ticket_arrival.lower() or ticket_arrival.lower() in arrival_station.lower()
        
        if not (date_match and departure_match and arrival_match):
            print(f"   SECURITY BLOCK: Ticket details don't match journey")
            print(f"   Journey: {journey_date}, {departure_station} → {arrival_station}")
            print(f"   Ticket:  {ticket_date}, {ticket_departure} → {ticket_arrival}")
            return False
            
        print("Ticket matches journey details")
        return True
        
    except Exception as e:
        print(f"SECURITY WARNING: Error validating ticket match - {str(e)}")
        return False


async def create_browser_session():
    """Create a properly configured browser session for delay repay automation"""
    return BrowserSession(
        headless=False,  
        user_data_dir=None,  
        viewport={'width': 1280, 'height': 720},
        keep_alive=True,  
        allowed_domains=ALLOWED_DOMAINS,
    )

async def create_controller():
    """Create controller with file upload capability for ticket uploads"""
    from browser_use import Controller, ActionResult
    import asyncio
    import os
    
    controller = Controller()
    
    @controller.action('Upload ticket')
    async def upload_ticket(file_path: str, page):
        try:
            if not file_path:
                print(f"Error: Empty file path provided")
                return ActionResult(extracted_content="Failed: Empty file path")
                
            abs_path = os.path.abspath(file_path)
            print(f"\nAttempting to upload file: {abs_path}")
            
            if not os.path.exists(abs_path):
                print(f"Error: File does not exist at path: {abs_path}")
                return ActionResult(extracted_content=f"Failed: File not found at {abs_path}")
            
            print(f"File exists and has size: {os.path.getsize(abs_path)} bytes")
            

            result = await page.evaluate(build_file_input_js())
            if result:
                print("Made file input visible with JavaScript")
                file_input = await page.wait_for_selector('input[type="file"]', timeout=5000)
                
                if file_input:
                    print(f"Found file input, setting file: {abs_path}")
                    await file_input.set_input_files(abs_path)
                    print("Successfully set input files")
                    
                    # Brief pause to allow upload to process - EXACT OpenAI timing
                    await asyncio.sleep(2)
                    
                    return ActionResult(
                        extracted_content=f"Upload successful: {os.path.basename(abs_path)}",
                        include_in_memory=True
                    )
                else:
                    print("Error: Could not find file input element even after making it visible")
                    return ActionResult(extracted_content="Failed: Could not find file input element")
            else:
                print("Error: No file input elements found on page")
                return ActionResult(extracted_content="Failed: No file input elements found")
                
        except Exception as e:
            print(f"Unexpected error in upload_ticket: {str(e)}")
            return ActionResult(extracted_content=f"Failed to upload ticket: {str(e)}")
    
    return controller

async def run_type_a_automation(
    journey_details: dict,
    passenger_details: dict,
    bank_details: dict,
    ticket_image_path: str
):
    
    browser_session = await create_browser_session()
    
    try:
        llm = ChatOpenAI(model="gpt-4.1", temperature=0.1) 
        
        controller = await create_controller()
        print("✅ Controller created for file uploads")
        
        operator_website = get_operator_website(journey_details["train_operator"])

        login_agent = Agent(
            task=build_login_prompt(operator_website, DELAY_REPAY_EMAIL, DELAY_REPAY_PASSWORD),
            llm=llm,
            browser_session=browser_session,
            use_vision=True
        )
        
        await login_agent.run()
        print("Login completed")
        
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

        print(f"Delay: {delay_minutes} minutes → Looking for range: {delay_range}")

        journey_agent = Agent(
            task=build_journey_details_prompt(journey_date, departure_station, arrival_station, departure_time, delay_range, delay_minutes),
            llm=llm,
            browser_session=browser_session,
            use_vision=True
        )
        
        await journey_agent.run()
        print("Journey details entered")

        print("Starting ticket selection and upload...")
        ticket_agent = Agent(
            task=build_ticket_details_prompt(ticket_image_path),
            llm=llm,
            browser_session=browser_session,
            controller=controller,  
            use_vision=True,
        )
        
        ticket_result = await ticket_agent.run()
        print(f"Ticket upload completed: {ticket_result}")

        print("Starting final review...")
        review_agent = Agent(
            task=build_review_prompt(passenger_details, bank_details, departure_station, arrival_station, journey_date, departure_time, delay_minutes),
            llm=llm,
            browser_session=browser_session,
            use_vision=True,
        )
        
        review_result = await review_agent.run()
        print(f"Review completed: {review_result}")
        
    finally:
        if browser_session:
            await browser_session.close()
            print("Browser session closed")


async def main():
    """
    Main function to test the Type A automation with eticket_test1.png
    """
    try:
        image_path = get_data_path("eticket_test1.png")
        
        if not os.path.exists(image_path):
            absolute_path = os.path.abspath(image_path)
            print(f"\nWARNING: The ticket image was not found at: {image_path}")
            print(f"Absolute path tried: {absolute_path}")
            print("Please ensure the image exists before running the script.")
            print("You may need to update the path in get_data_path() function.")
            raise FileNotFoundError(f"Ticket image not found: {image_path}")
            
        # Get absolute path and file info
        abs_image_path = os.path.abspath(image_path)
        file_size = os.path.getsize(abs_image_path)
        print(f"\nUsing ticket image: {abs_image_path}")
        print(f"File size: {file_size} bytes")
        print(f"File exists: {os.path.exists(abs_image_path)}")
        
        ticket_data = Delay_calc(image_path)
        ticket_data["image_path"] = abs_image_path  # Use absolute path
        
        # Use the EXACT date from the ticket - NO fallbacks
        original_date = ticket_data["ticket_date"]  # Will raise KeyError if missing
        ticket_data["date"] = original_date  # Keep the original date
        print(f"\nUsing original ticket date: {original_date}")
        
        # Check if this is a Type A TOC
        toc = ticket_data["train_operator"]  # Will raise KeyError if missing
        if not is_type_a_toc(toc):
            print(f"TOC '{toc}' is not a Type A TOC. Supported Type A TOCs:")
            for toc_name in TYPE_A_TOCS.keys():
                print(f"   - {toc_name}")
            return
        
        print(f"TOC '{toc}' is supported by Type A automation")
        
        journey_details = {
            "train_operator": ticket_data["train_operator"],
            "date": ticket_data["date"],
            "departure_time": ticket_data["departure_time"],
            "departure_station": ticket_data["departure_station"],
            "arrival_station": ticket_data["arrival_station"],
            "delay_minutes": ticket_data["delay_minutes"]  
        }
        
        passenger_details = {
            "title": "Mr",
            "first_name": "Test",
            "last_name": "User",
            "address_line1": "123 Test Street",
            "town_city": "Test City",
            "postcode": "TE5T 1NG",
            "country": "United Kingdom",
        }
        
        bank_details = {
            "account_holder": "Test User",
            "sort_code": "12-34-56",
            "account_number": "12345678"
        }
        
        print(f"\nStarting Type A automation for {toc}...")
        print(f"Journey: {journey_details['departure_station']} → {journey_details['arrival_station']}")
        print(f"Date: {journey_details['date']}")
        print(f"Time: {journey_details['departure_time']}")
        print(f"Delay: {journey_details['delay_minutes']} minutes")
        
        await run_type_a_automation(
            journey_details,
            passenger_details,
            bank_details,
            ticket_data["image_path"]
        )
        
        print("\nType A automation completed successfully!")
        print("The claim has been prepared and is ready for review.")
        print("Remember: This is for testing purposes. Review all details before submitting in production.")
        
    except KeyError as e:
        print(f"\nEXTRACTION ERROR: Missing required ticket data: {e}")
        print("The ticket extraction failed to provide all necessary information.")
        print("Automation cannot proceed without complete ticket data.")
    except Exception as e:
        print(f"\nERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 