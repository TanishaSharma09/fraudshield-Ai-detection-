"""FraudShield AI - Database Initialisation Script.

Executes schema.sql and populates:
- Users and behavioral baseline profiles from JSON seeds.
- Role-based application users (ADMIN and ANALYST accounts) with salted, hashed passwords.
- Model metrics baseline telemetry.
- Enforces SQLite WAL mode and foreign key constraints.
"""

import json
from datetime import datetime, timezone
from backend.core.config import settings
from backend.core.security import hash_password
from database.connection import get_db_connection


def format_user_metadata(upi_id: str) -> tuple[str, str, str]:
    """Generates clean human-readable name, email, and phone for seed users."""
    prefix = upi_id.split("@")[0].replace(".", " ").title()
    email_user = upi_id.split("@")[0].lower()
    clean_email = f"{email_user}@banksecure.in"
    phone_map = {
        "arjun.sharma@okaxis": "+91-9820012345",
        "priya.verma@okhdfcbank": "+91-9845023456",
        "rahul.kumar@paytm": "+91-9811034567",
        "sneha.patel@icici": "+91-9825045678",
        "mule.account.fake@ybl": "+91-9999900000",
    }
    phone = phone_map.get(upi_id.strip().lower(), "+91-9800000000")
    return prefix, clean_email, phone


def init_database(db_path: str | None = None) -> None:
    """Creates database tables and populates baseline profiles and initial accounts."""
    settings.ensure_directories()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # 1. Read and execute schema DDL
        if settings.SCHEMA_PATH.exists():
            schema_sql = settings.SCHEMA_PATH.read_text(encoding="utf-8")
            cursor.executescript(schema_sql)

        now = datetime.now(timezone.utc).isoformat()

        # 2. Seed initial application users (ADMIN and ANALYST)
        cursor.execute("SELECT COUNT(*) AS count FROM app_users;")
        app_user_count = cursor.fetchone()["count"]

        if app_user_count == 0:
            # Seed Admin Account
            admin_pwd_hash = hash_password(settings.DEFAULT_ADMIN_PASSWORD)
            cursor.execute(
                """
                INSERT INTO app_users 
                (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ADMIN', 1, ?, ?)
                ON CONFLICT(username) DO NOTHING;
                """,
                (
                    settings.DEFAULT_ADMIN_USERNAME,
                    settings.DEFAULT_ADMIN_EMAIL,
                    "Security Administrator",
                    admin_pwd_hash,
                    now,
                    now,
                ),
            )

            # Seed Analyst Account
            analyst_pwd_hash = hash_password(settings.DEFAULT_ANALYST_PASSWORD)
            cursor.execute(
                """
                INSERT INTO app_users 
                (username, email, full_name, hashed_password, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'ANALYST', 1, ?, ?)
                ON CONFLICT(username) DO NOTHING;
                """,
                (
                    settings.DEFAULT_ANALYST_USERNAME,
                    settings.DEFAULT_ANALYST_EMAIL,
                    "Senior SOC Analyst",
                    analyst_pwd_hash,
                    now,
                    now,
                ),
            )

        # 3. Seed baseline payment users
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        user_count = cursor.fetchone()["count"]

        seed_file = settings.SEEDS_DIR / "baseline_profiles.json"
        if user_count == 0 and seed_file.exists():
            seeds = json.loads(seed_file.read_text(encoding="utf-8"))
            for profile in seeds:
                upi = profile["upi_id"].strip().lower()
                full_name, email, phone = format_user_metadata(upi)
                cursor.execute(
                    """
                    INSERT INTO users 
                    (upi_id, full_name, email, phone, avg_amount, std_amount, total_transactions,
                     known_devices_json, typical_cities_json, last_seen, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(upi_id) DO NOTHING;
                    """,
                    (
                        upi,
                        full_name,
                        email,
                        phone,
                        profile["avg_amount"],
                        profile["std_amount"],
                        profile["total_transactions"],
                        profile["known_devices_json"],
                        profile["typical_cities_json"],
                        now,
                        now,
                        now,
                    ),
                )

        # 4. Seed user_profiles mirror table if empty
        cursor.execute("SELECT COUNT(*) AS count FROM user_profiles;")
        profile_count = cursor.fetchone()["count"]
        if profile_count == 0 and seed_file.exists():
            seeds = json.loads(seed_file.read_text(encoding="utf-8"))
            for profile in seeds:
                cursor.execute(
                    """
                    INSERT INTO user_profiles 
                    (upi_id, avg_amount, std_amount, total_transactions, known_devices_json, typical_cities_json, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(upi_id) DO NOTHING;
                    """,
                    (
                        profile["upi_id"].strip().lower(),
                        profile["avg_amount"],
                        profile["std_amount"],
                        profile["total_transactions"],
                        profile["known_devices_json"],
                        profile["typical_cities_json"],
                        now,
                    ),
                )

        # 5. Initialize default model metric entry if empty
        cursor.execute("SELECT COUNT(*) AS count FROM model_metrics;")
        metric_count = cursor.fetchone()["count"]
        if metric_count == 0:
            cursor.execute(
                """
                INSERT INTO model_metrics 
                (model_name, version, contamination, total_evaluated, total_flagged, accuracy_score)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                ("IsolationForest-UPI", "1.0.0", 0.035, 0, 0, 0.972),
            )


if __name__ == "__main__":
    init_database()
    print(f"Database successfully initialised at: {settings.DATABASE_PATH}")
