import base64
import csv
import json
import os

from openai import OpenAI

from src.delay_ease.builders.prompt_builder import build_ticket_extraction_prompt


def get_openai_credentials():
    """Get OpenAI credentials with fail-fast validation"""
    api_key = os.environ.get("OPENAI_API_KEY")
    organization = os.environ.get("OPENAI_ORGANIZATION")
    project = os.environ.get("OPENAI_PROJECT")

    if not api_key:
        raise ValueError("Missing required environment variable: OPENAI_API_KEY")

    return api_key, organization, project


def get_data_path(filename):
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    if filename.endswith(".csv"):
        return os.path.join(base_dir, "data", "reference_data", filename)
    elif (
        "test" in filename.lower()
        or filename.startswith("eticket_test")
        or filename.startswith("ticket_test")
    ):
        return os.path.join(base_dir, "data", "test_tickets", filename)
    else:
        return os.path.join(base_dir, "data", filename)


def get_test_ticket_path(filename):
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base_dir, "data", "test_tickets", filename)


def get_reference_data_path(filename):
    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    return os.path.join(base_dir, "data", "reference_data", filename)


def load_stations(csv_filename=None) -> dict:
    """load station data from csv - returns dict keyed by station name"""
    if csv_filename is None:
        csv_filename = get_reference_data_path("stations.csv")

    stations = {}
    with open(csv_filename, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            station = row["stationName"].strip().upper()
            crs = row["crsCode"].strip().upper()
            stations[station] = {"crs": crs, "name": row["stationName"].strip()}
    return stations


def build_crs_to_station(stations: dict) -> dict:
    """reverse mapping from crs code to station name"""
    crs_to_station = {}
    for station_data in stations.values():
        crs_to_station[station_data["crs"]] = station_data["name"]
    return crs_to_station


def validate_segment(segment: dict, stations: dict, crs_to_station: dict) -> dict:
    dep_station = segment.get("departure_station", "")
    dep_crs = segment.get("departure_crs", "")

    # handle none values
    if dep_station is None:
        dep_station = ""
    if dep_crs is None:
        dep_crs = ""

    dep_station = dep_station.strip()
    dep_crs = dep_crs.strip().upper()

    if dep_station:
        key = dep_station.upper()
        if key in stations:
            segment["departure_crs"] = stations[key]["crs"]
        else:
            return {"error": f"departure station '{dep_station}' not found"}
    elif dep_crs:
        if dep_crs in crs_to_station:
            segment["departure_station"] = crs_to_station[dep_crs]
        else:
            return {"error": f"departure crs '{dep_crs}' not found"}
    else:
        return {"error": "departure station and crs both missing"}

    arr_station = segment.get("arrival_station", "")
    arr_crs = segment.get("arrival_crs", "")

    if arr_station is None:
        arr_station = ""
    if arr_crs is None:
        arr_crs = ""

    arr_station = arr_station.strip()
    arr_crs = arr_crs.strip().upper()

    if arr_station:
        key = arr_station.upper()
        if key in stations:
            segment["arrival_crs"] = stations[key]["crs"]
        else:
            return {"error": f"arrival station '{arr_station}' not found"}
    elif arr_crs:
        if arr_crs in crs_to_station:
            segment["arrival_station"] = crs_to_station[arr_crs]
        else:
            return {"error": f"arrival crs '{arr_crs}' not found"}
    else:
        return {"error": "arrival station and crs both missing"}

    return segment


def validate_extracted_data(extracted_data: dict, stations_csv_filename=None) -> dict:
    """validate ticket data against stations csv"""
    if stations_csv_filename is None:
        stations_csv_filename = get_data_path("stations.csv")

    stations = load_stations(stations_csv_filename)
    crs_to_station = build_crs_to_station(stations)

    if "segments" in extracted_data:
        # multi leg journey
        validated_segments = []
        for seg in extracted_data["segments"]:
            result = validate_segment(seg, stations, crs_to_station)
            if "error" in result:
                return result
            validated_segments.append(result)
        extracted_data["segments"] = validated_segments
    else:
        # single journey
        result = validate_segment(extracted_data, stations, crs_to_station)
        if "error" in result:
            return result
        extracted_data.update(result)

    return extracted_data


def extract_ticket_details(image_path: str) -> dict:
    """extract ticket info from image using openai vision"""

    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")

    data_url = f"data:image/png;base64,{base64_image}"

    prompt = build_ticket_extraction_prompt()

    api_key, organization, project = get_openai_credentials()

    client = OpenAI(
        api_key=api_key,
        organization=organization,
        project=project,
    )

    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        max_tokens=500,
    )

    details_json = response.choices[0].message.content
    extracted_data = json.loads(details_json)

    # skip validation for paper tickets
    if "segments" in extracted_data:
        for segment in extracted_data["segments"]:
            if segment.get("ticket_format") == "Paper":
                return extracted_data
    else:
        if extracted_data.get("ticket_format") == "Paper":
            return extracted_data

    # validate against station database
    validated_data = validate_extracted_data(extracted_data)
    if "error" in validated_data:
        return {
            "error": f"photo unclear: {validated_data['error']} please upload clearer photo"
        }

    return validated_data
