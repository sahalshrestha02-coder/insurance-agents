from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from main import run_automation
from db import get_policyholder, POLICYHOLDERS
from pydantic import BaseModel
from typing import List, Optional
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Insurance Renewal Automation API")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
import pathlib
static_dir = pathlib.Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# LLM for chatbot
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GEMINI_API_KEY"))

# Policy context from POLICY.md
POLICY_CONTEXT = ""
policy_path = pathlib.Path(__file__).parent / "POLICY.md"
if policy_path.exists():
    POLICY_CONTEXT = policy_path.read_text()

class PolicyholderResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    policy_id: str
    renewal_date: str
    days_remaining: int
    renewal_status: str
    preferred_channel: str
    history: List[str]

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.get("/")
def serve_frontend():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Insurance Renewal Automation API is running"}

@app.get("/policyholders")
def list_policyholders():
    return {"policyholders": list(POLICYHOLDERS.values())}

@app.get("/dashboard/stats")
def get_stats():
    stats = {"EMAIL_SENT": 0, "WHATSAPP_SENT": 0, "VOICE_CALL_MADE": 0, "ESCALATED": 0, "PENDING": 0}
    for ph in POLICYHOLDERS.values():
        status = ph.get("renewal_status", "PENDING")
        if status in stats:
            stats[status] += 1
        else:
            stats["PENDING"] += 1
    return stats

@app.post("/renew/{policyholder_id}")
def trigger_renewal(policyholder_id: str):
    ph_data = get_policyholder(policyholder_id)
    if not ph_data:
        raise HTTPException(status_code=404, detail=f"Policyholder {policyholder_id} not found")
    try:
        run_automation(policyholder_id)
        updated_data = get_policyholder(policyholder_id)
        return {"status": "success", "data": updated_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholder/{policyholder_id}", response_model=PolicyholderResponse)
def get_status(policyholder_id: str):
    ph_data = get_policyholder(policyholder_id)
    if not ph_data:
        raise HTTPException(status_code=404, detail=f"Policyholder {policyholder_id} not found")
    return ph_data

@app.post("/chat", response_model=ChatResponse)
def chat_with_policy(request: ChatRequest):
    system_prompt = f"""You are a helpful insurance policy assistant for our company. 
Answer questions based on the following company policy document. Be concise and friendly.

POLICY DOCUMENT:
{POLICY_CONTEXT}

If the question is not related to the policy, politely redirect to policy topics."""
    
    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=request.message)
        ])
        return {"reply": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
