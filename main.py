# main.py
from typing import Dict, Any, List
from langgraph.graph import StateGraph, START, END
from agents import (
    AgentState, 
    data_retrieval_node, 
    strategy_node, 
    email_agent_node, 
    voice_agent_node, 
    whatsapp_agent_node,
    guardrail_agent_node,
    hitl_node
)

# Initialize the state graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("data_retrieval", data_retrieval_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("email", email_agent_node)
workflow.add_node("voice", voice_agent_node)
workflow.add_node("whatsapp", whatsapp_agent_node)
workflow.add_node("guardrail", guardrail_agent_node)
workflow.add_node("hitl", hitl_node)

# Add edges
workflow.add_edge(START, "data_retrieval")
workflow.add_edge("data_retrieval", "strategy")

# Conditional edges from strategy
def router(state: AgentState):
    return state["next_node"]

workflow.add_conditional_edges(
    "strategy",
    router,
    {
        "email": "email",
        "voice": "voice",
        "whatsapp": "whatsapp",
        "hitl": "hitl"
    }
)

# Guardrail routing
def guardrail_router(state: AgentState):
    if state["guardrail_status"] == "APPROVED":
        return "end"
    else:
        return "hitl"

workflow.add_edge("email", "guardrail")
workflow.add_edge("whatsapp", "guardrail")
workflow.add_conditional_edges(
    "guardrail",
    guardrail_router,
    {
        "end": END,
        "hitl": "hitl"
    }
)

# End edges
workflow.add_edge("voice", END)
workflow.add_edge("hitl", END)

# Compile the graph
app = workflow.compile()

def run_automation(ph_id: str):
    print(f"\n--- PROCESSING AUTOMATION FOR {ph_id} ---")
    initial_state = {
        "messages": [],
        "policyholder_id": ph_id,
        "policyholder_data": {},
        "next_node": "",
        "communication_channel": "",
        "status": "",
        "guardrail_status": ""
    }
    
    # Run the graph
    for output in app.stream(initial_state):
        # Optional: Print intermediate state for debugging
        # print(output)
        pass

if __name__ == "__main__":
    # Test with different policyholders to verify time-based thresholds
    run_automation("PH_EMAIL")    # 30 days -> Email -> Critic
    run_automation("PH_WHATSAPP") # 15 days -> WhatsApp -> Critic
    run_automation("PH_VOICE")    # 7 days -> Voice
    run_automation("PH_HITL")     # 2 days -> HITL
