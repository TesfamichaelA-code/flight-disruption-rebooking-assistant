"""The shared state that every node in the graph reads from and writes to."""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


# To describe the shape of all data flowing through the graph
class RebookingState(TypedDict, total=False):
    # To hold the incoming request (written by the caller when invoking the graph)
    request_id: str
    booking_ref: str
    message: str  # the passenger's latest message

    # To keep the whole conversation, including the Rebooking Agent's tool calls.
    # add_messages is a reducer: new messages are APPENDED instead of overwriting.
    messages: Annotated[list, add_messages]

    # To hold the booking (written once by intake, then reused on follow-ups)
    booking: dict

    # To hold what the classifier understood
    intent: str  # "rebook" | "refund" | "compensation" | "complaint"
    constraints: dict  # for example {"latest_arrival": "2026-10-04T12:00", "notes": "..."}

    # To hold the solution an agent proposed (a flight, a refund or a compensation)
    proposed_solution: dict | None

    # To hold the policy check result
    policy_passed: bool | None
    policy_failure_reason: str
    retry_count: int  # failed policy checks for this request (3 = first try + 2 retries -> escalate)

    # To hold the escalation result
    escalated: bool
    escalation_note: str  # handover note for a human agent

    # To hold the reply sent to the passenger
    final_response: str
