

def build_ticket_extraction_prompt() -> str:
    prompt = (
        "Analyze this train ticket image. First, determine if this is a PAPER ticket or an E-TICKET/M-TICKET:\n"
        "- Paper tickets: Physical tickets that were printed on paper/cardstock, scanned or photographed\n"
        "- E-tickets/M-tickets: Digital tickets displayed on phone/computer screens, screenshots, or digital PDFs\n\n"
        
        "If the ticket shows a single journey leg, "
        "return a JSON dictionary with these keys exactly: "
        "'ticket_format' (either 'Paper' or 'E-ticket'), "
        "'ticket_date', 'departure_time', 'departure_station', 'departure_crs', "
        "'arrival_station', 'arrival_crs', 'ticket_type', 'railcard', and 'ctr'. "
        
        "If the ticket shows multiple segments, return a JSON dictionary with one key 'segments', "
        "whose value is an array of dictionaries, each with the same keys as above (including 'ticket_format'). "
        
        "Formatting rules (mandatory): "
        "ticket_date MUST be 'DD Mon YYYY' (e.g., '10 Jul 2025') — do NOT use 'YYYY-MM-DD' or 'DD/MM/YYYY'. "
        "departure_time MUST be 24-hour 'HH:MM' with leading zeros (e.g., '09:05'). "
        
        "If the ticket mentions 'London Terminals' but also includes a seat reservation or itinerary "
        "showing a more specific arrival station (e.g., 'London King's Cross'), use that specific station "
        "in 'arrival_station' and the corresponding station code (e.g., 'KGX') in 'arrival_crs'. "
        
        "IMPORTANT: Be very accurate about ticket_format - this determines if the automation will proceed. "
        "Paper tickets should only be marked as 'Paper' if they are clearly physical tickets that were scanned. "
        "Screenshots, mobile displays, or digital images should be marked as 'E-ticket'. "
        
        "Return only valid JSON. Do not include any code blocks, triple backticks, or extra text."
    )
    return prompt


def build_login_prompt(operator_website: str, DELAY_REPAY_EMAIL: str, DELAY_REPAY_PASSWORD: str) -> str:
    login_task = f"""
Navigate to the delay repay website and log in:

1. Go to the URL: {operator_website}
2. Wait for the page to fully load (look for the login form to appear)
3. Find the login form fields
4. Enter the email: {DELAY_REPAY_EMAIL}
5. Enter the password: {DELAY_REPAY_PASSWORD}
6. Find and click the login/submit button 
7. Wait for the login to complete and verify you are successfully logged in
8. STOP HERE - Do not proceed to make a claim yet

IMPORTANT RULES:
- ONLY work with the delay repay website at {operator_website}
- NEVER navigate to Google or any other website
- Stop immediately after successful login
- Do NOT click "Make a claim" or fill out any forms - that's for the next agent
- Just verify you are logged in and then STOP
- Wait for each page to fully load before proceeding
"""
    return login_task
    


def build_journey_details_prompt(journey_date: str, departure_station: str, arrival_station: str, departure_time: str, delay_range: str, delay_minutes: int) -> str:
    journey_task = f"""
CRITICAL: You are already logged in and on the delay repay website. DO NOT navigate away from this website.

You are continuing from where the login agent left off. Complete the journey details:

1. Click the "Make a claim" button to start a new claim
2. You will be on a journey details form with fields for date, stations, and time
3. IMPORTANT: If an "Info" popup appears, close it by clicking the X button
4. Select the date: 11 August 2025 (11/8/2025) using the calendar widget
5. Enter the departure station: {departure_station} in the "From" field
6. Enter the arrival station: {arrival_station} in the "To" field
7. Enter the scheduled departure time: {departure_time} in the "Leaving at" field
8. Click the Search button to find journeys
9. Select the journey: {departure_station} to {arrival_station} {departure_time}
10. Select the delay range: "{delay_range}" (covering {delay_minutes} minutes)

STOP after selecting the delay range - the ticket agent will continue.

IMPORTANT RULES:
- You are already logged in - do not try to log in again
- NEVER navigate to Google or any other website
- Do NOT click question mark buttons or info buttons - they open confusing popups
- If you accidentally open an info popup, immediately close it with the X button before continuing
- Ignore any help text or question mark icons
- Wait for each field to be validated before moving to the next one
- If any error messages appear, read and address them before continuing
- STOP after selecting the delay range - do not continue to ticket selection
"""
    return journey_task


def build_ticket_details_prompt(ticket_image_path: str) -> str:
    ticket_task = f"""
CRITICAL: You are already logged in and on the delay repay website. DO NOT navigate away from this website.

You are continuing from where the journey agent left off. Complete the ticket details section and upload the image of the ticket:

1. We are only claiming for one ticket, so when asked "Are you claiming for more than one ticket?" - select "No" 
2. The ticket type we will be claiming for is E-ticket - select "E-ticket" or "E-ticket/M-ticket"  
3. The ticket duration is a single ticket - when duration options appear, select "Single" 
4. The image of the ticket is required for proof - you will see a button allowing for ticket upload. Use "Upload ticket" action with: {ticket_image_path}
5. After upload completes, click "Confirm" button to validate the ticket
6. STOP HERE - Do not proceed further, the next agent will continue

IMPORTANT: 
- WAIT for each page navigation to complete before proceeding
- Use the custom "Upload ticket" action for file uploads
- Do NOT click question mark buttons or info buttons - they open confusing popups
- If you accidentally open an info popup, immediately close it with the X button before continuing
- STOP after confirming the ticket upload - the compensation agent will handle the rest
- Stay on current delay repay website only
"""
    return ticket_task


def build_review_prompt(passenger_details: dict, bank_details: dict, departure_station: str, arrival_station: str, journey_date: str, departure_time: str, delay_minutes: int) -> str:
    review_task = f"""
Complete the final review and details for delay repay claim:

PASSENGER DETAILS - Ensure these are correctly entered:
- Title: {passenger_details['title']}
- First Name: {passenger_details['first_name']}
- Last Name: {passenger_details['last_name']}
- Address: {passenger_details['address_line1']}
- Town/City: {passenger_details['town_city']}
- Postcode: {passenger_details['postcode']}
- Country: {passenger_details.get('country', 'United Kingdom')}

COMPENSATION METHOD - Ensure bank transfer details are correct:
- Payment Method: Bank Transfer
- Account Holder: {bank_details['account_holder']}
- Sort Code: {bank_details['sort_code']}
- Account Number: {bank_details['account_number']}

VERIFY (do not change):
- Journey: {departure_station} to {arrival_station} on {journey_date} at {departure_time}
- Delay: {delay_minutes} minutes
- Ticket: E-ticket/M-ticket (Single)
- Upload: Ticket image uploaded successfully

CRITICAL: Review all details carefully but DO NOT submit the claim. Stop at the final review page.
"""
    return review_task