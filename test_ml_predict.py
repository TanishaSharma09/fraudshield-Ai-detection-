from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import create_access_token
from datetime import datetime, timezone

admin_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})

now_iso = datetime.now(timezone.utc).isoformat()
tx_susp = {
    "tx_id": "TXN_AUDIT_SUSP_01",
    "sender_upi": "sneha.reddy@okicici",
    "receiver_upi": "unknown.crypto.mule@ybl",
    "amount": 98500.0,
    "channel": "COLLECT_REQ",
    "device_id": "DEV-EMULATOR-ROOTED-99",
    "ip_address": "194.26.29.112",
    "location_city": "Moscow",
    "timestamp": now_iso
}
resp2 = client.post("/api/predict", json=tx_susp)
print("Detail:", resp2.json())
