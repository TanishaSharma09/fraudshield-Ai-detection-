"""E2E Verification for Investigate Alert Functionality."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_investigate_alert_e2e_flow():
    client = TestClient(app)

    # 1. Login as admin
    login_res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@FraudShield2026!'})
    assert login_res.status_code == 200
    token = login_res.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Trigger high risk simulation preset
    sim_res = client.post('/api/simulation/preset', json={'preset': 'SIM_SWAP_DRAIN'}, headers=headers)
    assert sim_res.status_code == 201
    sim_data = sim_res.json()
    tx_id = sim_data['tx_id']
    alert_id = sim_data.get('alert_id')
    assert alert_id is not None, 'alert_id should be generated for SIM_SWAP_DRAIN'

    # 3. Retrieve alert details via GET /api/alerts/{alert_id}
    get_res = client.get(f'/api/alerts/{alert_id}', headers=headers)
    assert get_res.status_code == 200
    alert_data = get_res.json()
    assert alert_data['alert_id'] == alert_id
    assert alert_data['tx_id'] == tx_id
    assert alert_data['amount'] == 88000.0
    assert alert_data['sender_upi'] == 'sneha.reddy@okicici'
    assert 'fraud.cashout' in alert_data['receiver_upi']
    assert alert_data['channel'] == 'UPI_APP'
    assert alert_data['device_id'] == 'DEV-UNKNOWN-ROOTED-ANDROID'
    assert alert_data['severity'] in ['HIGH', 'CRITICAL']
    assert alert_data['risk_score'] >= 80.0
    assert len(alert_data['explanations']) >= 1
    assert alert_data['status'] == 'PENDING'

    # 4. Retrieve alert details via GET /api/alerts/{tx_id}
    get_by_tx = client.get(f'/api/alerts/{tx_id}', headers=headers)
    assert get_by_tx.status_code == 200
    assert get_by_tx.json()['alert_id'] == alert_id

    # 5. SOC Investigation Action: Mark as REVIEWED
    rev_res = client.patch(
        f'/api/alerts/{alert_id}',
        json={'action': 'REVIEW', 'notes': 'Analyst examining SIM swap indicators', 'reviewed_by': 'admin'},
        headers=headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()['status'] == 'REVIEWED'
    assert rev_res.json()['reviewed_by'] == 'admin'

    # 6. SOC Investigation Action: BLOCK
    block_res = client.patch(
        f'/api/alerts/{alert_id}',
        json={'action': 'BLOCK', 'notes': 'Confirmed unauthorized account takeover', 'reviewed_by': 'admin'},
        headers=headers,
    )
    assert block_res.status_code == 200
    assert block_res.json()['status'] == 'BLOCK'

    # 7. Check alert summary
    summary_res = client.get('/api/alerts/summary', headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary['total'] >= 1
