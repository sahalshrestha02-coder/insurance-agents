# db.py
from typing import Dict, Any

POLICYHOLDERS: Dict[str, Dict[str, Any]] = {
    "PH_EMAIL": {
        "id": "PH_EMAIL",
        "name": "John 30-Day",
        "email": "sahalshrestha02@gmail.com",
        "phone": "+919718556121",
        "policy_id": "POL030",
        "renewal_date": "2025-04-01",
        "days_remaining": 30,
        "renewal_status": "PENDING",
        "preferred_channel": "EMAIL",
        "history": []
    },
    "PH_WHATSAPP": {
        "id": "PH_WHATSAPP",
        "name": "Bob 15-Day",
        "email": "sahalshrestha02@gmail.com",
        "phone": "+919718556121",
        "policy_id": "POL015",
        "renewal_date": "2025-03-17",
        "days_remaining": 15,
        "renewal_status": "PENDING",
        "preferred_channel": "WHATSAPP",
        "history": []
    },
    "PH_VOICE": {
        "id": "PH_VOICE",
        "name": "Jane 7-Day",
        "email": "jane7@example.com",
        "phone": "+919718556121",
        "policy_id": "POL007",
        "renewal_date": "2025-03-09",
        "days_remaining": 7,
        "renewal_status": "PENDING",
        "preferred_channel": "VOICE",
        "history": []
    },
    "PH_HITL": {
        "id": "PH_HITL",
        "name": "Alice 2-Day",
        "email": "alice2@example.com",
        "phone": "+919718556121",
        "policy_id": "POL002",
        "renewal_date": "2025-03-04",
        "days_remaining": 2,
        "renewal_status": "PENDING",
        "preferred_channel": "EMAIL",
        "history": []
    }
}

def get_policyholder(ph_id: str) -> Dict[str, Any]:
    return POLICYHOLDERS.get(ph_id)

def update_policyholder(ph_id: str, updates: Dict[str, Any]):
    if ph_id in POLICYHOLDERS:
        POLICYHOLDERS[ph_id].update(updates)
