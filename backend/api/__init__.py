"""FraudShield AI REST API Routes Package."""

from backend.api import routes_health
from backend.api import routes_transactions
from backend.api import routes_predict
from backend.api import routes_alerts
from backend.api import routes_analytics
from backend.api import routes_simulation
from backend.api import routes_auth
from backend.api import routes_users

__all__ = [
    "routes_health",
    "routes_transactions",
    "routes_predict",
    "routes_alerts",
    "routes_analytics",
    "routes_simulation",
    "routes_auth",
    "routes_users",
]
