"""Runs all 4 test scenarios and the follow-up message.

Usage:  python main.py
Output: printed to the terminal and saved to results.md; the diagram is saved to graph.mmd
"""

from langgraph.checkpoint.memory import MemorySaver

from graph import build_graph


# To list the test runs: (title, thread_id, input). Same thread_id = same conversation.
SCENARIOS = [
    (
        "Scenario 1: Cancelled flight, must arrive by noon",
        "passenger-XK9L2P",
        {
            "request_id": "R-7702",
            "booking_ref": "XK9L2P",
            "message": "My flight to Dubai was cancelled. I need to be there by tomorrow noon.",
        },
    ),
    (
        "Scenario 1 follow-up: same thread, no booking reference given",
        "passenger-XK9L2P",
        {
            "request_id": "R-7703",
            "message": "Actually, can I get a refund instead?",
        },
    ),
    (
        "Scenario 2: 6-hour delay, asks about compensation",
        "passenger-DL3M7Q",
        {
            "request_id": "R-7704",
            "booking_ref": "DL3M7Q",
            "message": "My flight is delayed 6 hours. Am I entitled to anything?",
        },
    ),
    (
        "Scenario 3: Only business-class seats available",
        "passenger-BZ4Q8M",
        {
            "request_id": "R-7705",
            "booking_ref": "BZ4Q8M",
            "message": "My flight to Nairobi was cancelled. Please put me on another flight.",
        },
    ),
    (
        "Scenario 4: Complaint asking for a manager",
        "passenger-MG5T1R",
        {
            "request_id": "R-7706",
            "booking_ref": "MG5T1R",
            "message": "This is the third time you've cancelled on me. I want to speak to a manager.",
        },
    ),
]


def run_scenario(graph, title: str, thread_id: str, request: dict) -> str:
    # To tell the checkpointer which conversation to load and save
    # (recursion_limit is a safety net on the total number of steps)
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}

    # To run the graph step by step and record which node ran and which tools were called
    path = []
    tool_calls = []
    for update in graph.stream(request, config, stream_mode="updates"):
        for node_name, changes in update.items():
            path.append(node_name)
            for message in (changes or {}).get("messages", []):
                for call in getattr(message, "tool_calls", []):
                    tool_calls.append(f"{call['name']}({call['args']})")

    # To read the final saved state for this thread
    state = graph.get_state(config).values

    # To build a readable report of this run
    report = "\n".join([
        f"## {title}",
        "",
        f"**thread_id:** `{thread_id}`",
        "",
        f"**Input message:** {request['message']}",
        "",
        f"**Path:** {' → '.join(path)}",
        "",
        f"**Tools called:** {', '.join(tool_calls) or 'none'}",
        "",
        f"**Intent:** {state.get('intent')}  |  **Policy passed:** {state.get('policy_passed')}  |  "
        f"**Failed checks (retry_count):** {state.get('retry_count')}  |  **Escalated:** {state.get('escalated')}",
        "",
        f"**Last policy failure reason:** {state.get('policy_failure_reason') or 'none'}",
        "",
        f"**Proposed solution:** `{state.get('proposed_solution')}`",
        "",
        "**Final response:**",
        "",
        state.get("final_response", ""),
        "",
    ])
    print(report)
    print("-" * 80)
    return report


def main():
    # To build the graph with an in-memory checkpointer (saves state per thread_id)
    graph = build_graph(checkpointer=MemorySaver())

    # To print and save the graph diagram
    diagram = graph.get_graph().draw_mermaid()
    print(diagram)
    with open("graph.mmd", "w") as file:
        file.write(diagram)

    # To run every scenario and collect the reports
    reports = [run_scenario(graph, title, thread_id, request) for title, thread_id, request in SCENARIOS]

    # To save all results so they can be pasted into the README
    with open("results.md", "w") as file:
        file.write("# Scenario results\n\n" + "\n".join(reports))
    print("Saved results.md and graph.mmd")


if __name__ == "__main__":
    main()
