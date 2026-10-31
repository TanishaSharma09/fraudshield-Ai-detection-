"""FraudShield AI - Frontend Integration Test Suite.

Verifies that the static UI assets are correctly mounted and served by FastAPI,
and that all 9 required fintech cybersecurity components and disclaimers are present.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_ui_index_served_successfully():
    """Verifies GET /ui/ returns 200 OK and renders index.html."""
    response = client.get("/ui/")
    assert response.status_code == 200
    html = response.text

    # 1. Sidebar navigation
    assert 'class="sidebar"' in html
    assert 'FraudShield' in html
    assert 'id="sidebar-alert-badge"' in html

    # 2. Top navigation bar
    assert 'class="topbar"' in html
    assert 'id="global-search-input"' in html
    assert 'id="live-polling-toggle"' in html

    # 3. Overview dashboard
    assert 'Cybersecurity Operations Center' in html
    assert 'UI Demonstration Baseline' in html
    assert 'Notice:' in html

    # 4. Summary statistic cards (4 KPI cards)
    assert 'kpi-cards-grid' in html
    assert 'id="kpi-total-evaluated"' in html
    assert 'id="kpi-total-flagged"' in html
    assert 'id="kpi-pending-alerts"' in html

    # 5. Transaction activity chart
    assert 'id="activityChart"' in html

    # 6. Risk distribution chart
    assert 'id="riskDistributionChart"' in html

    # 7. Recent transaction table
    assert 'id="transactions-table"' in html
    assert 'id="transactions-tbody"' in html
    assert 'id="ledger-filter-tabs"' in html

    # 8. Recent fraud alerts
    assert 'id="alerts-list-container"' in html
    assert 'Actionable Fraud Alerts' in html

    # 9. User profile area
    assert 'id="user-profile-chip"' in html
    assert 'id="user-drawer-backdrop"' in html


def test_transaction_management_section_components():
    """Verifies that the dedicated transaction management view, table, filters, and states are present."""
    response = client.get("/ui/")
    assert response.status_code == 200
    html = response.text

    # Dedicated view
    assert 'id="view-transactions"' in html
    assert 'Transaction Surveillance & Management' in html

    # Table and Columns
    assert 'id="mgmt-transactions-table"' in html
    assert 'id="mgmt-transactions-tbody"' in html
    assert 'Sender Identifier' in html
    assert 'Receiver Identifier' in html
    assert 'data-sort="amount"' in html
    assert 'data-sort="timestamp"' in html
    assert 'data-sort="risk_score"' in html
    assert 'data-sort="tx_id"' in html

    # Search and Filter Toolbar
    assert 'id="mgmt-search-input"' in html
    assert 'id="mgmt-filter-risk"' in html
    assert 'id="mgmt-filter-channel"' in html
    assert 'id="mgmt-filter-status"' in html
    assert 'id="mgmt-start-date"' in html
    assert 'id="mgmt-end-date"' in html
    assert 'id="btn-reset-filters"' in html

    # Loading, Empty, and Error States
    assert 'id="mgmt-loading-state"' in html
    assert 'id="mgmt-empty-state"' in html
    assert 'id="mgmt-error-state"' in html
    assert 'id="btn-error-retry"' in html

    # Pagination Controls
    assert 'id="mgmt-pagination-container"' in html
    assert 'id="mgmt-page-first"' in html
    assert 'id="mgmt-page-prev"' in html
    assert 'id="mgmt-page-next"' in html
    assert 'id="mgmt-page-last"' in html
    assert 'id="mgmt-page-size"' in html

    # Transaction Details Modal
    assert 'id="tx-detail-modal"' in html
    assert 'id="tx-modal-content"' in html


def test_simulation_stream_controls():
    """Verifies that the real-time simulation stream controls, speed adjustments, and safety disclaimers exist."""
    response = client.get("/ui/")
    assert response.status_code == 200
    html = response.text

    # Control Deck
    assert 'id="simulation-control-deck"' in html
    assert 'Real-Time UPI Transaction Stream Simulator' in html

    # Start, Pause, Resume, Stop buttons
    assert 'id="btn-sim-start"' in html
    assert 'id="btn-sim-pause"' in html
    assert 'id="btn-sim-resume"' in html
    assert 'id="btn-sim-stop"' in html

    # Speed adjustment controls
    assert 'id="sim-speed-slider"' in html
    assert 'id="sim-speed-val"' in html

    # Scenario Mode Selector
    assert 'id="sim-scenario-select"' in html
    assert 'NORMAL_PAYMENT' in html
    assert 'UNUSUALLY_LARGE' in html
    assert 'VELOCITY_BURST' in html
    assert 'NEW_RECIPIENT' in html
    assert 'UNUSUAL_PATTERN' in html

    # Telemetry Counters
    assert 'id="sim-metric-total"' in html
    assert 'id="sim-metric-flagged"' in html
    assert 'id="sim-metric-rate"' in html

    # Simulation Disclaimers & Safety
    assert 'Simulated Environment' in html
    assert 'Zero connection to real banks' in html


def test_static_css_assets_served():
    """Verifies that all three CSS design files are served with status 200."""
    for css_file in ["css/main.css", "css/dashboard.css", "css/components.css"]:
        resp = client.get(f"/ui/{css_file}")
        assert resp.status_code == 200
        assert len(resp.text) > 100


def test_static_js_assets_served():
    """Verifies that all four client JavaScript files are served with status 200."""
    for js_file in ["js/api.js", "js/charts.js", "js/simulator.js", "js/dashboard.js"]:
        resp = client.get(f"/ui/{js_file}")
        assert resp.status_code == 200
        assert len(resp.text) > 100


def test_demonstration_disclaimer_integrity():
    """Verifies demonstration disclaimers prevent false claims about preview numbers."""
    resp = client.get("/ui/js/api.js")
    assert resp.status_code == 200
    assert "Demonstration preview baseline data" in resp.text

    index_resp = client.get("/ui/")
    assert "Initial dashboard charts and summary statistics display realistic demonstration data" in index_resp.text


def test_theme_toggle_controls_and_defaults():
    """Verifies that the light theme is default and dark/light toggle controls are present."""
    resp = client.get("/ui/")
    assert resp.status_code == 200
    html = resp.text

    # Default light theme anti-flash setup
    assert "localStorage.getItem('fraudshield_theme') || 'light'" in html

    # Settings modal theme toggle options
    assert 'id="settings-modal"' in html
    assert 'id="btn-theme-light"' in html
    assert 'id="btn-theme-dark"' in html
    assert 'id="theme-status-badge"' in html

    # Topbar quick theme action
    assert 'id="btn-topbar-theme-toggle"' in html

    # Main CSS defines both default light tokens and data-theme="dark" overrides
    css_resp = client.get("/ui/css/main.css")
    assert css_resp.status_code == 200
    assert ":root" in css_resp.text
    assert 'html[data-theme="dark"]' in css_resp.text
