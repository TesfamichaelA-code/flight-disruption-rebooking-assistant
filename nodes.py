"""The graph's nodes. Each node takes the state and returns only the fields it changed."""

import os
from datetime import datetime, timedelta
from typing import Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel, Field

from prompts import (
    CLASSIFIER_PROMPT,
    COMPENSATION_PROMPT,
    ESCALATION_PROMPT,
    FINAL_RESPONSE_PROMPT,
    REBOOKING_EXTRACT_PROMPT,
    REBOOKING_PROMPT,
    REBOOKING_RETRY_MESSAGE,
    REFUND_PROMPT,
    RETRY_FEEDBACK,
)
from state import RebookingState
from tools import CURRENT_TIME, find_flight, get_booking, get_fare_rules, search_flights


# ---------------------------------------------------------------------------
# LLM setup
# ---------------------------------------------------------------------------

# To read GROQ_API_KEY and MODEL_NAME from the .env file
load_dotenv()

# To stay under the Groq free-tier limits (about 1 request every 5 seconds)
rate_limiter = InMemoryRateLimiter(requests_per_second=0.2)

# To create the one Groq model every agent shares (temperature 0 = repeatable answers)
llm = init_chat_model(
    os.getenv("MODEL_NAME", "openai/gpt-oss-120b"),
    model_provider="groq",
    temperature=0,
    rate_limiter=rate_limiter,
    timeout=60,  # To give up on a request that hangs for 60s (it is then retried)
)

# To give the Rebooking Agent its tools (the LLM only REQUESTS them; the ToolNode runs them)
REBOOKING_TOOLS = [get_booking, search_flights]
llm_with_tools = llm.bind_tools(REBOOKING_TOOLS)


# ---------------------------------------------------------------------------
# Structured output schemas (what we want the LLM to return)
# ---------------------------------------------------------------------------

# To get the classifier's answer as clean fields instead of free text
class ClassifiedRequest(BaseModel):
    intent: Literal["rebook", "refund", "compensation", "complaint"]
    latest_arrival: str | None = Field(None, description="Latest arrival as YYYY-MM-DDTHH:MM, or null")
    notes: str | None = Field(None, description="Any other constraint, or null")


# To get the Rebooking Agent's chosen flight as clean fields
class FlightChoice(BaseModel):
    flight_number: str = Field(description="Proposed flight number, or empty string if none")
    cabin: str = Field(description="Proposed cabin: economy, premium_economy, business or first")


# To get a refund or compensation proposal as clean fields
class AmountProposal(BaseModel):
    amount_usd: float
    explanation: str


# ---------------------------------------------------------------------------
# 1. Intake
# ---------------------------------------------------------------------------

def intake(state: RebookingState) -> dict:
    # To load the booking only on the first message; a follow-up reuses the saved one
    booking = state.get("booking") or get_booking.invoke({"booking_ref": state["booking_ref"]})

    # To add the new message to the history and start this request with a clean slate
    return {
        "booking": booking,
        "messages": [HumanMessage(state["message"])],
        "proposed_solution": None,
        "policy_passed": None,
        "policy_failure_reason": "",
        "retry_count": 0,
        "escalated": False,
        "escalation_note": "",
        "final_response": "",
    }


# ---------------------------------------------------------------------------
# 2. Request Classifier Agent
# ---------------------------------------------------------------------------

def classifier(state: RebookingState) -> dict:
    # To ask the LLM for the intent and constraints in a fixed schema
    prompt = CLASSIFIER_PROMPT.format(current_time=CURRENT_TIME, message=state["message"])
    result = llm.with_structured_output(ClassifiedRequest).invoke(prompt)

    # To save only the classifier's own fields (routing happens in graph.py, not here)
    return {
        "intent": result.intent,
        "constraints": {"latest_arrival": result.latest_arrival, "notes": result.notes},
    }


# ---------------------------------------------------------------------------
# 3. Rebooking Agent (LLM + tools, loops with the ToolNode)
# ---------------------------------------------------------------------------

def rebooking_agent(state: RebookingState) -> dict:
    new_messages = []

    # To pass the policy checker's reason back on a retry
    # (it is a retry when a failure reason exists and we did NOT just come back from the tools)
    last_message = state["messages"][-1]
    if state.get("policy_failure_reason") and not isinstance(last_message, ToolMessage):
        reason = state["policy_failure_reason"]
        new_messages.append(HumanMessage(REBOOKING_RETRY_MESSAGE.format(reason=reason)))

    # To let the LLM decide the next step: call a tool, or give its final answer
    system_prompt = SystemMessage(REBOOKING_PROMPT.format(
        current_time=CURRENT_TIME,
        booking_ref=state["booking"]["booking_ref"],
        constraints=state["constraints"],
    ))
    response = llm_with_tools.invoke([system_prompt] + state["messages"] + new_messages)
    new_messages.append(response)

    # To keep looping: if the LLM asked for a tool, tools_condition sends us to the ToolNode
    if response.tool_calls:
        return {"messages": new_messages}

    # To turn the final answer into a proposal the policy checker can check
    return {"messages": new_messages, "proposed_solution": build_rebooking_proposal(response.text)}


def build_rebooking_proposal(answer: str) -> dict:
    # To pull the flight number and cabin out of the agent's final answer
    prompt = REBOOKING_EXTRACT_PROMPT.format(answer=answer)
    choice = llm.with_structured_output(FlightChoice).invoke(prompt)

    # To attach the real flight details from the mock data (times, cabins, connection)
    flight_number = choice.flight_number.strip().upper()
    return {
        "type": "rebook",
        "flight_number": flight_number,
        "cabin": choice.cabin.strip().lower().replace(" ", "_"),
        "flight": find_flight(flight_number),
    }


# ---------------------------------------------------------------------------
# 4. Refund Agent
# ---------------------------------------------------------------------------

def refund_agent(state: RebookingState) -> dict:
    # To read the fare rules for this booking's fare type
    booking = state["booking"]
    fare_rules = get_fare_rules.invoke({"fare_type": booking["fare_type"]})

    # To ask the LLM for a refund amount (with the failure reason if this is a retry)
    prompt = REFUND_PROMPT.format(booking=booking, fare_rules=fare_rules, feedback=retry_feedback(state))
    result = llm.with_structured_output(AmountProposal).invoke(prompt)

    return {"proposed_solution": {
        "type": "refund",
        "amount_usd": result.amount_usd,
        "explanation": result.explanation,
    }}


# ---------------------------------------------------------------------------
# 5. Compensation Agent
# ---------------------------------------------------------------------------

def compensation_agent(state: RebookingState) -> dict:
    # To ask the LLM for a compensation amount based on the booking's delay
    prompt = COMPENSATION_PROMPT.format(booking=state["booking"], feedback=retry_feedback(state))
    result = llm.with_structured_output(AmountProposal).invoke(prompt)

    return {"proposed_solution": {
        "type": "compensation",
        "amount_usd": result.amount_usd,
        "explanation": result.explanation,
    }}


def retry_feedback(state: RebookingState) -> str:
    # To add the policy checker's reason to the prompt only when this is a retry
    if state.get("policy_failure_reason"):
        return RETRY_FEEDBACK.format(reason=state["policy_failure_reason"])
    return ""


# ---------------------------------------------------------------------------
# 6. Policy Checker (plain Python, no LLM)
# ---------------------------------------------------------------------------

# To compare cabins: a lower number is a lower cabin
CABIN_RANK = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}


def policy_checker(state: RebookingState) -> dict:
    # To pick the rule set that matches the request type
    intent = state["intent"]
    solution = state["proposed_solution"]
    booking = state["booking"]

    if intent == "rebook":
        problem = check_rebooking(solution, booking)
    elif intent == "refund":
        problem = check_refund(solution, booking)
    else:
        problem = check_compensation(solution, booking)

    # To record a pass
    if problem is None:
        return {"policy_passed": True, "policy_failure_reason": ""}

    # To record a fail: save the reason and count one more retry
    return {
        "policy_passed": False,
        "policy_failure_reason": problem,
        "retry_count": state["retry_count"] + 1,
    }


def check_rebooking(solution: dict, booking: dict) -> str | None:
    # To fail if the proposed flight does not exist
    flight = solution["flight"]
    if flight is None:
        return f"Flight '{solution['flight_number']}' was not found in the search results."

    # To fail if the proposed cabin is not sold on that flight
    cabin = solution["cabin"]
    if cabin not in flight["available_cabins"]:
        return f"Cabin '{cabin}' is not available on {flight['flight_number']}."

    # Rule: same cabin class or lower
    if CABIN_RANK.get(cabin, 99) > CABIN_RANK[booking["cabin_class"]]:
        return f"Cabin '{cabin}' is higher than the booked '{booking['cabin_class']}' cabin."

    # Rule: departs within 48 hours of the original departure
    original = datetime.fromisoformat(booking["departure"])
    new = datetime.fromisoformat(flight["departure"])
    if new - original > timedelta(hours=48):
        return f"{flight['flight_number']} departs more than 48 hours after the original flight."

    # Rule: connection time at least 60 minutes
    if flight["connection_minutes"] is not None and flight["connection_minutes"] < 60:
        return f"{flight['flight_number']} has a {flight['connection_minutes']}-minute connection (minimum is 60)."

    return None


def check_refund(solution: dict, booking: dict) -> str | None:
    # Rule: airline cancelled = full fare; passenger choice on a non-refundable fare = taxes only
    fare_rules = get_fare_rules.invoke({"fare_type": booking["fare_type"]})
    if booking["disruption"]["type"] == "cancelled" or fare_rules["refundable"]:
        expected = booking["fare_paid_usd"]
    else:
        expected = fare_rules["tax_amount_usd"]

    # To fail if the agent's amount is different from the rule
    if abs(solution["amount_usd"] - expected) > 0.01:
        return f"Refund must be ${expected}, not ${solution['amount_usd']}."
    return None


def check_compensation(solution: dict, booking: dict) -> str | None:
    # Rule: under 3h = $0, 3 to 6h = $200, over 6h or cancelled = $400
    disruption = booking["disruption"]
    if disruption["type"] == "cancelled" or disruption["delay_hours"] > 6:
        expected = 400
    elif disruption["delay_hours"] >= 3:
        expected = 200
    else:
        expected = 0

    # To fail if the agent's amount is different from the rule
    if abs(solution["amount_usd"] - expected) > 0.01:
        return f"Compensation must be ${expected}, not ${solution['amount_usd']}."
    return None


# ---------------------------------------------------------------------------
# 7. Escalation Agent
# ---------------------------------------------------------------------------

def escalation(state: RebookingState) -> dict:
    # To write a short handover note for a human agent
    prompt = ESCALATION_PROMPT.format(
        message=state["message"],
        booking=state["booking"],
        intent=state["intent"],
        proposed_solution=state.get("proposed_solution"),
        policy_failure_reason=state.get("policy_failure_reason") or "none",
        retry_count=state.get("retry_count", 0),
    )
    note = llm.invoke(prompt).text

    return {"escalated": True, "escalation_note": note}


# ---------------------------------------------------------------------------
# 8. Final Response Agent
# ---------------------------------------------------------------------------

def final_response(state: RebookingState) -> dict:
    # To only mention a solution to the passenger if it passed the policy check
    approved_solution = state["proposed_solution"] if state.get("policy_passed") else None

    # To write the reply to the passenger
    prompt = FINAL_RESPONSE_PROMPT.format(
        passenger=state["booking"]["passenger"],
        message=state["message"],
        intent=state["intent"],
        proposed_solution=approved_solution,
        escalated=state.get("escalated", False),
        escalation_note=state.get("escalation_note") or "none",
    )
    reply = llm.invoke(prompt).text

    # To save the reply and add it to the conversation history
    return {"final_response": reply, "messages": [AIMessage(reply)]}
