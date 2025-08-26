import csv
import json
import datetime
import requests
import base64
import os
from dotenv import load_dotenv
from ticket_data_extraction import extract_ticket_details, get_data_path
from const import HSP_SERVICE_METRICS_URL, HSP_SERVICE_DETAILS_URL

load_dotenv()

HSP_EMAIL = os.environ.get("HSP_EMAIL", "")
HSP_PASSWORD = os.environ.get("HSP_PASSWORD", "")

def hsp_auth_header(email, password):
    token = base64.b64encode(f"{email}:{password}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {token}"}

def get_service_metrics(from_loc, to_loc, from_time, to_time, from_date, to_date, days):
    headers = {"Content-Type": "application/json", **hsp_auth_header(HSP_EMAIL, HSP_PASSWORD)}
    payload = {
        "from_loc": from_loc.strip(),
        "to_loc": to_loc.strip(),
        "from_time": from_time.strip(),
        "to_time": to_time.strip(),
        "from_date": from_date.strip(),
        "to_date": to_date.strip(),
        "days": days.strip()
    }
    response = requests.post(HSP_SERVICE_METRICS_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def get_service_details(rid):
    headers = {"Content-Type": "application/json", **hsp_auth_header(HSP_EMAIL, HSP_PASSWORD)}
    payload = {"rid": rid.strip()}
    response = requests.post(HSP_SERVICE_DETAILS_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def find_service_by_dep_time(services, ticket_dep_time):
    ticket_dep_time = ticket_dep_time.strip()
    for service in services:
        svc_dep_time = service["serviceAttributesMetrics"].get("gbtt_ptd", "").strip()
        if svc_dep_time == ticket_dep_time:
            return service
    return None

def extract_delay_info(service_details, departure_crs, arrival_crs):
    dep_info = {}
    arr_info = {}
    toc_code = service_details["serviceAttributesDetails"].get("toc_code", "").strip()
    
    for loc in service_details["serviceAttributesDetails"].get("locations", []):
        if loc.get("location", "").strip() == departure_crs.strip():
            dep_info = {
                "I_gbtt_ptd": loc.get("gbtt_ptd", "").strip(),
                "I_gbtt_pta": loc.get("gbtt_pta", "").strip(),
                "I_actual_td": loc.get("actual_td", "").strip(),
                "I_actual_ta": loc.get("actual_ta", "").strip()
            }
        if loc.get("location", "").strip() == arrival_crs.strip():
            arr_info = {
                "F_gbtt_ptd": loc.get("gbtt_ptd", "").strip(),
                "F_gbtt_pta": loc.get("gbtt_pta", "").strip(),
                "F_actual_td": loc.get("actual_td", "").strip(),
                "F_actual_ta": loc.get("actual_ta", "").strip()
            }
    delay = None
    if arr_info.get("F_gbtt_pta") and arr_info.get("F_actual_ta"):
        try:
            fmt = "%H%M"
            sched_arrival = datetime.datetime.strptime(arr_info["F_gbtt_pta"], fmt)
            actual_arrival = datetime.datetime.strptime(arr_info["F_actual_ta"], fmt)
            delay = (actual_arrival - sched_arrival).total_seconds() / 60.0
        except Exception:
            delay = None
    result = {}
    result.update(dep_info)
    result.update(arr_info)
    result["arrival_delay_minutes"] = round(delay, 1) if delay is not None else None
    result["toc_code"] = toc_code
    return result

def load_tok_codes(csv_filename="toc_code.csv") -> dict:
    tok_dict = {}
    with open(get_data_path(csv_filename), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            code = row["Tok code"].strip().upper()
            company = row["Company Name"].strip()
            if code not in ["ZZ", "UNKNOWN", ""]:
                tok_dict[code] = company
    return tok_dict

def load_delay_repay(csv_filename="delay_repay_percentages_single_tickets.csv") -> dict:
    percentages = {}
    with open(get_data_path(csv_filename), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            operator = row["Company Name"].strip()
            percentages[operator] = {
                "15 - 29 Mins": row["15 - 29 Mins"].strip(),
                "30 - 59 Mins": row["30 - 59 Mins"].strip(),
                "60 - 119 Mins": row["60 - 119 Mins"].strip(),
                "120 + Mins": row["120 + Mins"].strip()
            }
    return percentages

def get_toc_minimum_delay(operator: str, csv_filename="delay_repay_percentages_single_tickets.csv") -> int:
    percentages = load_delay_repay(csv_filename)
    if operator not in percentages:
        return 15  
    
    if percentages[operator]["15 - 29 Mins"] != "0%":
        return 15
    elif percentages[operator]["30 - 59 Mins"] != "0%":
        return 30
    elif percentages[operator]["60 - 119 Mins"] != "0%":
        return 60
    elif percentages[operator]["120 + Mins"] != "0%":
        return 120
    else:
        return 999  

def get_delay_repay_percentage(delay_minutes: float, operator: str, csv_filename="delay_repay_percentages_single_tickets.csv") -> str:
    # use toc-specific minimum instead of hardcoded 15
    min_delay = get_toc_minimum_delay(operator, csv_filename)
    if delay_minutes < min_delay:
        return "0%"
    
    percentages = load_delay_repay(csv_filename)
    if operator in percentages:
        if 15 <= delay_minutes < 30:
            return percentages[operator]["15 - 29 Mins"]
        elif 30 <= delay_minutes < 60:
            return percentages[operator]["30 - 59 Mins"]
        elif 60 <= delay_minutes < 120:
            return percentages[operator]["60 - 119 Mins"]
        else:
            return percentages[operator]["120 + Mins"]
    else:
        return "Unknown"

def get_detailed_status_message(delay_minutes: float, operator: str, days_old: int, compensation_pct: str) -> dict:
    if days_old > 28:
        return {
            "status": "ineligible_age",
            "message": f"Your journey was {days_old} days ago, which exceeds the 28-day claim window. UK delay repay claims must be submitted within 28 days of travel.",
            "next_action": "learn_more",
            "learn_more_topic": "claim_deadlines"
        }
    
    min_delay = get_toc_minimum_delay(operator)
    
    if delay_minutes < min_delay:
        if min_delay == 999:
            return {
                "status": "ineligible_no_compensation",
                "message": f"{operator} does not offer delay repay compensation for any delay duration.",
                "next_action": "learn_more", 
                "learn_more_topic": "toc_policies"
            }
        else:
            return {
                "status": "ineligible_duration",
                "message": f"Your {delay_minutes}min delay with {operator} doesn't qualify. {operator} requires delays of {min_delay}+ minutes for compensation.",
                "next_action": "learn_more",
                "learn_more_topic": "toc_policies"
            }
    
    if compensation_pct == "0%":
        return {
            "status": "ineligible_bracket",
            "message": f"Your {delay_minutes}min delay falls in a 0% compensation bracket for {operator}.",
            "next_action": "learn_more",
            "learn_more_topic": "compensation_brackets"
        }
    
    return {
        "status": "eligible",
        "message": f"Great news! Your {delay_minutes}min delay with {operator} qualifies for {compensation_pct} compensation. We're processing your claim automatically.",
        "next_action": "proceed_claim",
        "compensation_percentage": compensation_pct
    }

def process_ticket_delay(ticket_data, toc_csv_filename="toc_code.csv", delay_csv_filename="delay_repay_percentages_single_tickets.csv") -> dict:
    tok_codes = load_tok_codes(toc_csv_filename)
    departure_crs = ticket_data["departure_crs"]
    arrival_crs = ticket_data["arrival_crs"]
    
    parsed_date = datetime.datetime.strptime(ticket_data["ticket_date"], "%d %b %Y")
    days_old = (datetime.datetime.now() - parsed_date).days
    
    if days_old > 28:
        status_info = get_detailed_status_message(0, "Unknown", days_old, "0%")
        ticket_data["delay_status"] = "Ticket is older than 28 days"  
        ticket_data.update(status_info)  
        return ticket_data
    
    hsp_date = parsed_date.strftime("%Y-%m-%d")
    ticket_dep_time = ticket_data["departure_time"].replace(":", "")
    
    dep_hour = int(ticket_dep_time[:2])
    from_time_str = f"{max(dep_hour - 1, 0):02d}00"
    to_time_str = f"{min(dep_hour + 1, 23):02d}59"
    
    weekday_index = parsed_date.weekday()
    if weekday_index < 5:
        days = "WEEKDAY"
    elif weekday_index == 5:
        days = "SATURDAY"
    else:
        days = "SUNDAY"
    
    try:
        metrics_data = get_service_metrics(
            from_loc=departure_crs,
            to_loc=arrival_crs,
            from_time=from_time_str,
            to_time=to_time_str,
            from_date=hsp_date,
            to_date=hsp_date,
            days=days
        )
    except Exception as e:
        ticket_data["delay_status"] = f"Metrics API error: {e}"
        ticket_data.update({
            "status": "error_api",
            "message": f"Unable to verify delays due to a technical issue: {e}. Please try again later.",
            "next_action": "retry"
        })
        return ticket_data

    services = metrics_data.get("Services", [])
    if not services:
        ticket_data["delay_status"] = "No matching services"
        ticket_data.update({
            "status": "error_no_services",
            "message": "No matching train services found for your journey. This may be due to incomplete schedule data.",
            "next_action": "manual_check"
        })
        return ticket_data

    matching_service = find_service_by_dep_time(services, ticket_dep_time)
    if matching_service is None:
        ticket_data["delay_status"] = "No matching service found"
        ticket_data.update({
            "status": "error_no_match",
            "message": "Could not find your specific train service. Please ensure your ticket details are clear and try again.",
            "next_action": "upload_clearer_photo"
        })
        return ticket_data

    rid_list = matching_service["serviceAttributesMetrics"]["rids"]
    matching_rid = rid_list[0]
    service_details = get_service_details(matching_rid)

    delay_info = extract_delay_info(service_details, departure_crs, arrival_crs)
    if delay_info.get("arrival_delay_minutes") is None:
        ticket_data["delay_status"] = "Delay data unavailable"
        ticket_data.update({
            "status": "error_no_delay_data",
            "message": "Delay information is not available for this journey. This may be due to incomplete performance data.",
            "next_action": "manual_check"
        })
        return ticket_data
    else:
        ticket_data["delay_minutes"] = delay_info["arrival_delay_minutes"]
        # map toc code to full operator name
        toc_code = delay_info.get("toc_code", "").strip()
        if toc_code and toc_code.upper() in tok_codes:
            operator_full = tok_codes[toc_code.upper()]
        else:
            operator_full = "Unknown"
        ticket_data["train_operator"] = operator_full
        
        # get compensation percentage based on delay and operator
        comp_pct = get_delay_repay_percentage(delay_info["arrival_delay_minutes"], operator_full, delay_csv_filename)
        ticket_data["compensation_percentage"] = comp_pct
        
        status_info = get_detailed_status_message(delay_info["arrival_delay_minutes"], operator_full, days_old, comp_pct)
        ticket_data.update(status_info)
        
        min_delay = get_toc_minimum_delay(operator_full, delay_csv_filename)
        if delay_info["arrival_delay_minutes"] < min_delay or comp_pct == "0%":
            ticket_data["delay_status"] = "Delay does not qualify"
        else:
            ticket_data["delay_status"] = "Delayed"
    
    ticket_data.update(delay_info)
    return ticket_data

def filter_crucial_info(ticket_data):
    crucial_fields = [
        "ticket_date", "departure_time", "departure_station", "departure_crs",
        "arrival_station", "arrival_crs", "ticket_type", "railcard", "ctr",
        "delay_minutes", "train_operator", "toc_code", "delay_status", 
        "compensation_percentage", "arrival_delay_minutes", "ticket_format",
        # include new status fields
        "status", "message", "next_action", "learn_more_topic"
    ]
    
    # if it's a multi-leg journey, filter each segment
    if "segments" in ticket_data:
        filtered_segments = []
        for segment in ticket_data["segments"]:
            filtered_segment = {k: segment.get(k, "") for k in crucial_fields if k in segment}
            filtered_segments.append(filtered_segment)
        return {"segments": filtered_segments}
    else:
        # single leg journey - filter the ticket data directly
        return {k: ticket_data.get(k, "") for k in crucial_fields if k in ticket_data}

def calculate_delay_compensation(image_path, toc_csv_filename="toc_code.csv", delay_csv_filename="delay_repay_percentages_single_tickets.csv") -> dict:
    """main function - extract ticket data and calculate delay compensation"""
    extracted_data = extract_ticket_details(image_path)
    
    if "error" in extracted_data:
        return {
            "status": "error_extraction",
            "message": f"Could not read your ticket: {extracted_data['error']}",
            "next_action": "upload_clearer_photo"
        }
    
    ticket_format = extracted_data.get("ticket_format", "E-ticket")  # default to e-ticket for safety
    print(f"Detected ticket format: {ticket_format}")
    
    # mvp: block paper tickets
    if ticket_format == "Paper":
        blocked_result = {
            "ticket_format": "Paper",
            "delay_status": "Paper tickets are currently not supported. Please use E-tickets or M-tickets only for this MVP version.",
            "compensation_percentage": "N/A",
            "train_operator": "N/A",
            # add structured status for ui
            "status": "blocked_paper",
            "message": "Sorry, Delay EASE currently doesn't support paper tickets. Please upload an e-ticket or m-ticket (digital screenshot) instead.",
            "next_action": "upload_eticket"
        }
        for field in ["ticket_date", "departure_time", "departure_station", "arrival_station", "ticket_type"]:
            if field in extracted_data:
                blocked_result[field] = extracted_data[field]
        return blocked_result
    
    # if multi-leg, process each segment
    if "segments" in extracted_data:
        processed_segments = []
        for seg in extracted_data["segments"]:
            # check if this segment is a paper ticket
            seg_format = seg.get("ticket_format", "E-ticket")
            if seg_format == "Paper":
                # block paper tickets at segment level too
                seg["delay_status"] = "Paper tickets are currently not supported. Please use E-tickets or M-tickets only for this MVP version."
                seg["compensation_percentage"] = "N/A"
                seg["train_operator"] = "N/A"
                seg.update({
                    "status": "blocked_paper",
                    "message": "Paper ticket segment detected. Please use e-tickets only.",
                    "next_action": "upload_eticket"
                })
                processed_segments.append(seg)
            else:
                processed_seg = process_ticket_delay(seg, toc_csv_filename, delay_csv_filename)
                processed_segments.append(processed_seg)
        
        eligible_segments = [s for s in processed_segments if s.get("status") == "eligible"]
        result = {"segments": processed_segments}
        if eligible_segments:
            result.update({
                "status": "eligible_multileg",
                "message": f"Found {len(eligible_segments)} eligible segment(s) for compensation out of {len(processed_segments)} total segments.",
                "next_action": "proceed_claim"
            })
        else:
            result.update({
                "status": "ineligible_multileg", 
                "message": "None of your journey segments qualify for delay repay compensation.",
                "next_action": "learn_more"
            })
    else:
        result = process_ticket_delay(extracted_data, toc_csv_filename, delay_csv_filename)
    
    return filter_crucial_info(result)
