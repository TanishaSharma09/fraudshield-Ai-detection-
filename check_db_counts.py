from database.connection import query_all, query_one

tables = ['app_users', 'users', 'transactions', 'fraud_alerts', 'model_prediction_records', 'user_profiles']
for t in tables:
    r = query_one(f"SELECT COUNT(*) AS c FROM {t}")
    count = r['c'] if r else 0
    print(f"Table {t:<26}: {count} records")

print("\nApp Users:")
users = query_all("SELECT id, username, email, full_name, role, is_active FROM app_users")
for u in users:
    print(dict(u))
