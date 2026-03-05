from fastapi import FastAPI, HTTPException
from main import run_automation
from db import get_policyholder
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Insurance Renewal Automation API")

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

@app.get("/")
def read_root():
    return {"message": "Insurance Renewal Automation API is running"}

@app.post("/renew/{policyholder_id}")
def trigger_renewal(policyholder_id: str):
    ph_data = get_policyholder(policyholder_id)
    if not ph_data:
        raise HTTPException(status_code=404, detail=f"Policyholder {policyholder_id} not found")
    
    try:
        # Trigger the LangGraph automation
        run_automation(policyholder_id)
        
        # Fetch updated data
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
