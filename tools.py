"""Mock airline tools.

Every tool returns fixed fake data, so each scenario gives the same result
on every run. No real airline systems are called.
"""

from langchain_core.tools import tool


# To give the mock airline a fixed "now", so "tomorrow noon" always means the same time
CURRENT_TIME = "2026-10-03T09:00"


# To store the fake bookings (one per test scenario)
BOOKINGS = {
    # Scenario 1: cancelled flight to Dubai, passenger must arrive by tomorrow noon
    "XK9L2P": {
        "booking_ref": "XK9L2P",
        "passenger": "Abebe Kebede",
        "origin": "ADD",
        "destination": "DXB",
        "flight_number": "ET600",
        "departure": "2026-10-03T10:30",
        "cabin_class": "economy",
        "fare_type": "economy_saver",
        "fare_paid_usd": 520,
        "disruption": {"type": "cancelled", "delay_hours": 0},
    },
    # Scenario 2: flight delayed by 6 hours
    "DL3M7Q": {
        "booking_ref": "DL3M7Q",
        "passenger": "Hana Girma",
        "origin": "ADD",
        "destination": "LHR",
        "flight_number": "ET700",
        "departure": "2026-10-03T11:00",
        "cabin_class": "economy",
        "fare_type": "economy_flex",
        "fare_paid_usd": 890,
        "disruption": {"type": "delayed", "delay_hours": 6},
    },
    # Scenario 3: cancelled flight to Nairobi, only business class seats left
    "BZ4Q8M": {
        "booking_ref": "BZ4Q8M",
        "passenger": "Dawit Alemu",
        "origin": "ADD",
        "destination": "NBO",
        "flight_number": "ET306",
        "departure": "2026-10-03T12:00",
        "cabin_class": "economy",
        "fare_type": "economy_saver",
        "fare_paid_usd": 310,
        "disruption": {"type": "cancelled", "delay_hours": 0},
    },
    # Scenario 4: angry passenger who wants a manager
    "MG5T1R": {
        "booking_ref": "MG5T1R",
        "passenger": "Selam Tadesse",
        "origin": "ADD",
        "destination": "JNB",
        "flight_number": "ET809",
        "departure": "2026-10-03T14:00",
        "cabin_class": "economy",
        "fare_type": "economy_saver",
        "fare_paid_usd": 610,
        "disruption": {"type": "cancelled", "delay_hours": 0},
    },
}


# To store the fake flight search results, keyed by (origin, destination)
FLIGHTS = {
    ("ADD", "DXB"): [
        # Good option: direct, economy seats, arrives before noon tomorrow
        {
            "flight_number": "ET604",
            "departure": "2026-10-03T22:00",
            "arrival": "2026-10-04T03:30",
            "available_cabins": ["economy", "business"],
            "connection_airport": None,
            "connection_minutes": None,
        },
        # Bad option: arrives too late AND the connection is only 45 minutes
        {
            "flight_number": "ET612",
            "departure": "2026-10-03T23:30",
            "arrival": "2026-10-04T15:10",
            "available_cabins": ["economy"],
            "connection_airport": "JED",
            "connection_minutes": 45,
        },
    ],
    # Only business class is left on this route, so every proposal breaks policy
    ("ADD", "NBO"): [
        {
            "flight_number": "ET308",
            "departure": "2026-10-03T18:00",
            "arrival": "2026-10-03T20:10",
            "available_cabins": ["business"],
            "connection_airport": None,
            "connection_minutes": None,
        },
        {
            "flight_number": "KQ311",
            "departure": "2026-10-04T07:00",
            "arrival": "2026-10-04T09:05",
            "available_cabins": ["business"],
            "connection_airport": None,
            "connection_minutes": None,
        },
    ],
}


# To store the fake fare rules for each fare type
FARE_RULES = {
    "economy_saver": {"fare_type": "economy_saver", "refundable": False, "tax_amount_usd": 85},
    "economy_flex": {"fare_type": "economy_flex", "refundable": True, "tax_amount_usd": 95},
}


# To let agents look up a booking by its reference
@tool
def get_booking(booking_ref: str) -> dict:
    """Get a passenger's booking: passenger name, route, cabin class, fare type,
    fare paid and disruption details (cancelled or delayed, and delay hours)."""
    booking = BOOKINGS.get(booking_ref.strip().upper())
    if booking is None:
        return {"error": f"No booking found for reference {booking_ref}"}
    return booking


# To let the Rebooking Agent search for replacement flights
@tool
def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Search replacement flights between two airport codes (for example ADD and DXB).
    Returns flights with departure/arrival times, available cabins and connection details.
    `date` is the travel date as YYYY-MM-DD."""
    # The mock data is keyed by route only, so the date does not change the result
    return FLIGHTS.get((origin.strip().upper(), destination.strip().upper()), [])


# To let the Refund Agent read whether a fare is refundable and how much tax it has
@tool
def get_fare_rules(fare_type: str) -> dict:
    """Get the fare rules for a fare type: whether it is refundable and the tax amount in USD."""
    rules = FARE_RULES.get(fare_type)
    if rules is None:
        return {"error": f"No fare rules found for fare type {fare_type}"}
    return rules


# To find one flight's full details by its number (used by the code, not by the LLM)
def find_flight(flight_number: str) -> dict | None:
    for flights in FLIGHTS.values():
        for flight in flights:
            if flight["flight_number"] == flight_number:
                return flight
    return None
