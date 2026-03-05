import os
import requests
from twilio.rest import Client
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from db import get_policyholder, update_policyholder

load_dotenv()

# Define the state of the graph
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    policyholder_id: str
    policyholder_data: dict
    next_node: str
    communication_channel: str
    status: str
    guardrail_status: str # APPROVED, REJECTED, or feedback

# LLM setup
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

def data_retrieval_node(state: AgentState):
    """Retrieve policyholder data from the mock database."""
    ph_id = state.get("policyholder_id")
    data = get_policyholder(ph_id)
    if not data:
        return {"messages": [AIMessage(content=f"Error: Policyholder {ph_id} not found.")], "status": "FAILED"}
    return {"policyholder_data": data, "status": "IN_PROGRESS"}

def strategy_node(state: AgentState):
    """Decide the communication channel based on days remaining to renewal."""
    data = state.get("policyholder_data")
    days = data.get("days_remaining", 30)
    
    if days >= 30:
        channel = "EMAIL"
    elif days >= 15:
        channel = "WHATSAPP"
    elif days >= 3:
        channel = "VOICE"
    else:
        channel = "HITL"
        return {"next_node": "hitl", "communication_channel": channel}
    
    return {"next_node": channel.lower(), "communication_channel": channel}

def send_email(to_email: str, subject: str, body: str):
    """Helper to send a real email using SMTP."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    sender_email = os.getenv("SENDER_EMAIL", smtp_user)

    if not all([smtp_user, smtp_pass]):
        print(f"--- SKIPPING REAL EMAIL (Missing Credentials) ---")
        return False

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_email

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"--- REAL EMAIL SENT TO {to_email} ---")
        return True
    except Exception as e:
        print(f"--- ERROR SENDING EMAIL: {e} ---")
        return False

def email_agent_node(state: AgentState):
    """Generate and send a renewal email."""
    data = state.get("policyholder_data")
    prompt = f"Write a professional insurance renewal email for {data['name']} (Policy: {data['policy_id']}, Renewal Date: {data['renewal_date']})."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Send real email
    subject = f"Insurance Renewal Notice - Policy {data['policy_id']}"
    email_body = response.content
    success = send_email(data['email'], subject, email_body)
    
    if not success:
        print(f"--- FAILED TO SEND REAL EMAIL TO {data['email']} ---")
    
    update_policyholder(data['id'], {"renewal_status": "EMAIL_SENT", "history": data['history'] + ["EMAIL_SENT"]})
    return {"messages": [response], "status": "COMPLETED"}

def send_voice_call(to_number: str):
    """Helper to make a real voice call using Twilio."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    voice_url = os.getenv("TWILIO_VOICE_URL")

    if not all([account_sid, auth_token, voice_url]) or account_sid == "your_sid_here":
        print(f"--- SKIPPING REAL VOICE CALL (Missing Credentials) ---")
        return False

    try:
        client = Client(account_sid, auth_token)
        call = client.calls.create(
            url=voice_url,
            to=to_number,
            from_=(from_number or "+14155238886").replace("whatsapp:", "")
        )
        print(f"--- REAL VOICE CALL INITIATED TO {to_number} (SID: {call.sid}) ---")
        return True
    except Exception as e:
        print(f"--- ERROR INITIATING VOICE CALL: {e} ---")
        return False

def voice_agent_node(state: AgentState):
    """Simulate a voice call interaction."""
    data = state.get("policyholder_data")
    prompt = f"Simulate a short voice call transcript with {data['name']} for insurance renewal. The goal is to ask if they want to renew."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Send real voice call
    success = send_voice_call(data['phone'])
    
    if not success:
        print(f"--- FAILED TO INITIATE REAL VOICE CALL TO {data['phone']} ---")
    
    update_policyholder(data['id'], {"renewal_status": "VOICE_CALL_MADE", "history": data['history'] + ["VOICE_CALL_MADE"]})
    return {"messages": [response], "status": "COMPLETED"}

def send_whatsapp(to_number: str, body: str):
    """Helper to send a real WhatsApp message using Twilio."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    if not all([account_sid, auth_token]) or account_sid == "your_sid_here":
        print(f"--- SKIPPING REAL WHATSAPP (Missing Credentials) ---")
        return False

    try:
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_whatsapp_number,
            body=body,
            to=f"whatsapp:{to_number}"
        )
        print(f"--- REAL WHATSAPP SENT TO {to_number} (SID: {message.sid}) ---")
        return True
    except Exception as e:
        print(f"--- ERROR SENDING WHATSAPP: {e} ---")
        return False

def whatsapp_agent_node(state: AgentState):
    """Generate and send a WhatsApp message."""
    data = state.get("policyholder_data")
    prompt = f"Write a professional and friendly WhatsApp insurance renewal message for {data['name']} (Policy: {data['policy_id']}, Renewal Date: {data['renewal_date']}). Keep it concise as it is for WhatsApp."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # Send real WhatsApp
    whatsapp_body = response.content
    success = send_whatsapp(data['phone'], whatsapp_body)
    
    if not success:
        print(f"--- FAILED TO SEND REAL WHATSAPP TO {data['phone']} ---")
    
    update_policyholder(data['id'], {"renewal_status": "WHATSAPP_SENT", "history": data['history'] + ["WHATSAPP_SENT"]})
    return {"messages": [response], "status": "WAITING_FOR_CRITIC"}

def guardrail_agent_node(state: AgentState):
    """Structured guardrail check for tone, PII, and financial accuracy."""
    last_message = state["messages"][-1].content
    channel = state["communication_channel"]
    data = state["policyholder_data"]
    
    prompt = f"""As a Safety and Compliance Guardrail Agent, review the following {channel} message.
    
    POLICYHOLDER DATA:
    - Name: {data['name']}
    - Policy ID: {data['policy_id']}
    - Renewal Date: {data['renewal_date']}
    
    MESSAGE TO REVIEW:
    {last_message}
    
    GUARDRAIL RULES:
    1. PROFESSIONAL TONE: Must be professional, empathetic, and premium.
    2. DATA ACCURACY: Must NOT hallucinate policy IDs or dates not in the data.
    3. FINANCIAL PROMISES: Must NOT offer specific discounts or price changes.
    4. PII PROTECTION: Ensure no sensitive data other than name/policy ID is exposed.
    
    If the message passes all rules, respond with 'GUARDRAIL_PASSED'.
    If it fails, provide a specific reason starting with 'GUARDRAIL_FAILED: '.
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip()
    
    print(f"--- GUARDRAIL CHECK ({channel}) ---")
    print(result)
    print("------------------------------------")
    
    if "GUARDRAIL_PASSED" in result:
        return {"guardrail_status": "APPROVED", "status": "FINALIZED"}
    else:
        return {"guardrail_status": result, "status": "REJECTED_BY_GUARDRAIL"}

def hitl_node(state: AgentState):
    """Route to human staff for manual intervention."""
    data = state.get("policyholder_data")
    print(f"--- ESCALATED TO HUMAN (Staff Remaining: 20) FOR {data['name']} ---")
    
    update_policyholder(data['id'], {"renewal_status": "ESCALATED", "history": data['history'] + ["ESCALATED_TO_HUMAN"]})
    return {"messages": [AIMessage(content=f"Handed over to human staff for {data['name']}.")], "status": "ESCALATED"}
