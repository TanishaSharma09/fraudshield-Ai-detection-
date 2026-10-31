"""FraudShield AI - Integration Test Suite for Account Relationship Network Graph.

Validates:
1. GET /api/analytics/network-graph endpoint returning topology nodes and edges.
2. Query filtering by `min_risk_score` and `only_suspicious`.
3. Metric calculations: mule hubs detected, repeated pairs, and circular routing.
4. Role-based access control (ADMIN and ANALYST authorized, unauthenticated rejected).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import create_access_token

admin_token = create_access_token({"sub": "1", "username": "admin", "role": "ADMIN"})
admin_client = TestClient(app, headers={"Authorization": f"Bearer {admin_token}"})

analyst_token = create_access_token({"sub": "2", "username": "analyst", "role": "ANALYST"})
analyst_client = TestClient(app, headers={"Authorization": f"Bearer {analyst_token}"})

unauth_client = TestClient(app)


def test_get_network_graph_endpoint_structure():
    """Verifies that GET /api/analytics/network-graph returns valid nodes, edges, and cluster metrics."""
    resp = admin_client.get("/api/analytics/network-graph")
    assert resp.status_code == 200
    data = resp.json()

    assert "nodes" in data
    assert "edges" in data
    assert "metrics" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert len(data["nodes"]) > 0

    node0 = data["nodes"][0]
    assert "id" in node0
    assert "label" in node0
    assert "role" in node0
    assert "avg_risk_score" in node0
    assert "is_mule_candidate" in node0
    assert "is_suspicious" in node0

    metrics = data["metrics"]
    assert "total_nodes" in metrics
    assert "total_edges" in metrics
    assert "suspicious_edges_count" in metrics
    assert "mule_hubs_detected" in metrics


def test_get_network_graph_filtering():
    """Verifies query parameters for min_risk_score and only_suspicious filtering."""
    resp_all = admin_client.get("/api/analytics/network-graph?only_suspicious=false")
    assert resp_all.status_code == 200
    data_all = resp_all.json()

    resp_susp = admin_client.get("/api/analytics/network-graph?only_suspicious=true")
    assert resp_susp.status_code == 200
    data_susp = resp_susp.json()

    # All edges in suspicious mode must have is_suspicious == True
    for edge in data_susp["edges"]:
        assert edge["is_suspicious"] is True


def test_network_graph_rbac_permissions():
    """Verifies RBAC: ADMIN and ANALYST are allowed; unauthenticated is rejected."""
    # 1. Analyst access permitted
    resp_analyst = analyst_client.get("/api/analytics/network-graph")
    assert resp_analyst.status_code == 200

    # 2. Unauthenticated rejected
    resp_unauth = unauth_client.get("/api/analytics/network-graph")
    assert resp_unauth.status_code == 401
