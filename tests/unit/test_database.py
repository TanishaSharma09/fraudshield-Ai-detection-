"""Unit tests for SQLite database connection and initialisation."""

import pytest
from database.init_db import init_database
from database.connection import query_all, query_one
from backend.core.config import settings


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_database()


def test_database_tables_exist():
    tables = query_all("SELECT name FROM sqlite_master WHERE type='table';")
    names = [t["name"] for t in tables]
    assert "users" in names
    assert "transactions" in names
    assert "fraud_alerts" in names
    assert "model_prediction_records" in names
    assert "user_profiles" in names
    assert "model_metrics" in names


def test_users_and_profiles_seeded():
    users = query_all("SELECT upi_id FROM users;")
    assert len(users) >= 5
    vpas = [u["upi_id"] for u in users]
    assert "arjun.sharma@okaxis" in vpas

    profiles = query_all("SELECT upi_id FROM user_profiles;")
    assert len(profiles) >= 5
