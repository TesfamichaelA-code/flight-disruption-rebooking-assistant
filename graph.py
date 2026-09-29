"""Builds the LangGraph graph: nodes, edges and all routing decisions."""

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from nodes import (
    REBOOKING_TOOLS,
    classifier,
    compensation_agent,
    escalation,
    final_response,
    intake,
    policy_checker,
    rebooking_agent,
    refund_agent,
)
from state import RebookingState


# To stop the retry cycle: first try + 2 retries, then escalate
MAX_RETRIES = 2

# To know which agent handles (and re-tries) each intent
INTENT_TO_AGENT = {
    "rebook": "rebooking_agent",
    "refund": "refund_agent",
    "compensation": "compensation_agent",
}


# ---------------------------------------------------------------------------
# Routing functions (they only READ the state and return where to go next)
# ---------------------------------------------------------------------------

def route_by_intent(state: RebookingState) -> str:
    # To send the request to the right specialist; complaints go straight to escalation
    return state["intent"]


def route_after_policy(state: RebookingState) -> str:
    # To finish when the solution passed the policy check
    if state["policy_passed"]:
        return "final_response"

    # To give up after the retry limit, so the cycle always ends
    if state["retry_count"] > MAX_RETRIES:
        return "escalation"

    # To send the failed solution back to the same agent that proposed it
    return INTENT_TO_AGENT[state["intent"]]


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph(checkpointer=None):
    builder = StateGraph(RebookingState)

    # To register every step as a node
    builder.add_node("intake", intake)
    builder.add_node("classifier", classifier)
    builder.add_node("rebooking_agent", rebooking_agent)
    builder.add_node("tools", ToolNode(REBOOKING_TOOLS))
    builder.add_node("refund_agent", refund_agent)
    builder.add_node("compensation_agent", compensation_agent)
    builder.add_node("policy_checker", policy_checker)
    builder.add_node("escalation", escalation)
    builder.add_node("final_response", final_response)

    # To start every request at intake, then classify it
    builder.add_edge(START, "intake")
    builder.add_edge("intake", "classifier")

    # Routing decision 1: which specialist handles the request
    builder.add_conditional_edges("classifier", route_by_intent, {
        "rebook": "rebooking_agent",
        "refund": "refund_agent",
        "compensation": "compensation_agent",
        "complaint": "escalation",
    })

    # Routing decision 2 (tool loop): tool requested -> ToolNode, otherwise -> policy check
    # (tools_condition returns "__end__" when there is no tool call; we map that to policy_checker,
    #  which is why the diagram labels this edge "__end__")
    builder.add_conditional_edges("rebooking_agent", tools_condition, {
        "tools": "tools",
        END: "policy_checker",
    })
    builder.add_edge("tools", "rebooking_agent")  # the tool loop goes back to the agent

    # To send refund and compensation proposals to the policy check
    builder.add_edge("refund_agent", "policy_checker")
    builder.add_edge("compensation_agent", "policy_checker")

    # Routing decision 3 (the retry cycle): pass -> reply, fail -> retry, too many fails -> escalate
    builder.add_conditional_edges("policy_checker", route_after_policy, [
        "final_response",
        "escalation",
        "rebooking_agent",
        "refund_agent",
        "compensation_agent",
    ])

    # To always finish with a reply to the passenger
    builder.add_edge("escalation", "final_response")
    builder.add_edge("final_response", END)

    # To turn the builder into a runnable graph (the checkpointer saves state per thread_id)
    return builder.compile(checkpointer=checkpointer)
