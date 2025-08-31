import os
import sys
import json
import asyncio
import datetime
from pathlib import Path
from delay_calculation import calculate_delay_compensation
from browser_automation_type_a import run_type_a_automation,is_type_a_toc
from dotenv import load_dotenv

load_dotenv()

def get_user_details():

    return {
        "passenger": {
            "title": os.environ.get("USER_TITLE", "Mrs"),
            "first_name": os.environ.get("USER_FIRST_NAME", "Test"),
            "last_name": os.environ.get("USER_LAST_NAME", "User"),
            "address_line1": os.environ.get("USER_ADDRESS", "123 Test Street"),
            "town_city": os.environ.get("USER_CITY", "Test City"),
            "postcode": os.environ.get("USER_POSTCODE", "TE5T 1NG"),
            "country": os.environ.get("USER_COUNTRY", "United Kingdom"),
            "email": os.environ.get("USER_EMAIL", "test@example.com")
        },
        "bank": {
            "account_holder": os.environ.get("USER_ACCOUNT_HOLDER", "Test User"),
            "sort_code": os.environ.get("USER_SORT_CODE", "12-34-56"),
            "account_number": os.environ.get("USER_ACCOUNT_NUMBER", "12345678")
        }
    }

def save_claim_record(user_id: str, ticket_data: dict, claim_reference: str = None) -> str:
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
        "ticket_image_path": ticket_data.get("image_path", "")
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
        print("PAPER TICKET DETECTED")
        
        
        
    elif status.startswith("ineligible"):
        print("NOT ELIGIBLE FOR COMPENSATION")
        
        
        if "learn_more" in ticket_data.get("next_action", ""):
            print(f"\nLearn more about {ticket_data.get('learn_more_topic', 'delay repay policies')}")
            
    elif status == "eligible":
        compensation = ticket_data.get("compensation_percentage", "Unknown")
        delay = ticket_data.get("delay_minutes", 0)
        toc = ticket_data.get("train_operator", "Unknown")
        dep_station = ticket_data.get("departure_station", "Unknown")
        arr_station = ticket_data.get("arrival_station", "Unknown")
        dep_time = ticket_data.get("departure_time", "Unknown")
        journey_date = ticket_data.get("ticket_date", "Unknown")

        print("ELIGIBLE FOR COMPENSATION!")
        print("="*60)
        print(f"{message}")
        print(f"\nDetails:")
        print(f"   Operator: {toc}")
        print(f"   From: {dep_station}")
        print(f"   To: {arr_station}")
        print(f"   Date: {journey_date}")
        print(f"   Departure time: {dep_time}")
        print(f"   Delay: {delay} minutes")
        print(f"   Compensation: {compensation}")
        
        amount = ticket_data.get("compensation_amount")
        if amount:
            print(f"   Estimated amount: £{amount:.2f}")
            
    elif status.startswith("error"):
        print("ERROR PROCESSING TICKET")
        print(f"{message}")
        
    else:
        print(f"STATUS: {status.upper()}")
        print(f"{message}")

def process_single_ticket(image_path: str, user_id: str = "test_user") -> dict:
    print("DELAY EASE - AUTOMATED DELAY REPAY")
    print(f"Processing ticket: {os.path.basename(image_path)}")
    
    if not os.path.exists(image_path):
        return {
            "status": "error_file_not_found",
            "message": f"Ticket file not found: {image_path}",
            "next_action": "upload_valid_file"
        }
    
    try:
        # phase 1 & 2: extract ticket data and check eligibility
        print("Analyzing ticket and checking for delays...")
        ticket_data = calculate_delay_compensation(image_path)
        ticket_data["image_path"] = os.path.abspath(image_path)
        
        display_status_message(ticket_data)
        
        # phase 3: proceed with automation if eligible
        if ticket_data.get("status") == "eligible":
            toc = ticket_data.get("train_operator", "")
            
            if is_type_a_toc(toc):
                print(f"\n Proceeding with automated claim submission for {toc}...")
                
                journey_details = {
                    "train_operator": toc,
                    "date": ticket_data.get("ticket_date", ""),
                    "departure_time": ticket_data.get("departure_time", ""),
                    "departure_station": ticket_data.get("departure_station", ""),
                    "arrival_station": ticket_data.get("arrival_station", ""),
                    "delay_minutes": ticket_data.get("delay_minutes", 0)
                }
                
                user_details = get_user_details()
                
                # phase 4: run automation
                try:
                    print("Submitting claim automatically...")
                    claim_result = asyncio.run(run_type_a_automation(
                        journey_details,
                        user_details["passenger"],
                        user_details["bank"],
                        ticket_data["image_path"]
                    ))
                    
                    # phase 5: store claim record
                    claim_id = save_claim_record(user_id, ticket_data, "AUTO_SUBMITTED")
                    
                    print("CLAIM SUBMITTED SUCCESSFULLY!")
                    print(f"Claim ID: {claim_id}")
                    print(f"You will receive a notification when compensation is ready for withdrawal")
                    
                    ticket_data["claim_id"] = claim_id
                    ticket_data["automation_status"] = "submitted"
                    
                except Exception as e:
                    print(f"\nError during automation: {e}")
                    ticket_data["automation_status"] = "failed"
                    ticket_data["automation_error"] = str(e)
                    
            else:
                print(f"\n{toc} automation not yet available")
                print("Your claim details have been saved for manual processing")
                
                claim_id = save_claim_record(user_id, ticket_data, "MANUAL_REQUIRED") 
                ticket_data["claim_id"] = claim_id
                ticket_data["automation_status"] = "manual_required"
                
        elif ticket_data.get("status", "").startswith("ineligible"):
            claim_id = save_claim_record(user_id, ticket_data, "INELIGIBLE")
            ticket_data["claim_id"] = claim_id
            
        print("\n" + "="*60)
        return ticket_data
        
    except Exception as e:
        error_data = {
            "status": "error_processing",
            "message": f"Unexpected error: {str(e)}",
            "next_action": "contact_support"
        }
        display_status_message(error_data)
        return error_data

def main():
    """Main entry point for the Delay EASE workflow"""
    if len(sys.argv) < 2:
        print("Usage: python delay_ease_main.py <ticket_image_path> [user_id]")
        print("\nExample: python delay_ease_main.py data/test_tickets/eticket_test9.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else "test_user"
    
    result = process_single_ticket(image_path, user_id)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") 
    result_file = f"data/results/delay_ease_result_{timestamp}.json"
    os.makedirs("data/results", exist_ok=True)
    
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nFull result saved to: {result_file}")





def test_eticket_test():
    
    TEST_TICKET_FILE = "eticket_test1.png"  # Change to any ticket in test_tickets/

    print(f"TESTING DELAY EASE WITH {TEST_TICKET_FILE}")
    
    test_image_path = f"data/test_tickets/{TEST_TICKET_FILE}"
    test_user_id = f"test_user_{TEST_TICKET_FILE.replace('.png', '')}"
    
 
    result = process_single_ticket(test_image_path, test_user_id)
    

    print("TEST RESULTS SUMMARY")
    print(f"Tested: {TEST_TICKET_FILE}")
    print(f"Status: {result.get('status', 'Unknown')}")
    print(f"TOC: {result.get('train_operator', 'Unknown')}")
    print(f"Delay: {result.get('delay_minutes', 'Unknown')} minutes")
    print(f"Compensation: {result.get('compensation_percentage', 'Unknown')}")
    
    return result

if __name__ == "__main__":
    if len(sys.argv) == 1:
        test_eticket_test()
    elif len(sys.argv) >= 2 and sys.argv[1] == "test":
        test_eticket_test()
    else:
        main()