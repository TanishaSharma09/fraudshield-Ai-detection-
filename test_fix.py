from ml_model.behavioural.baseline_tracker import get_baseline_tracker

tracker = get_baseline_tracker()
profile = tracker.get_user_baseline_from_db("arjun.sharma@okaxis")
print("Before fix, total_prior_transactions:", profile.total_prior_transactions)

# If we include sender_upi in query:
from database.connection import query_all
sql = """
    SELECT 
        sender_upi,
        amount,
        receiver_upi,
        device_id,
        timestamp
    FROM transactions
    WHERE LOWER(sender_upi) = LOWER(?)
    ORDER BY timestamp ASC;
"""
records = [dict(r) for r in query_all(sql, ("arjun.sharma@okaxis",))]
fixed_profile = tracker.compute_baseline_from_records("arjun.sharma@okaxis", records)
print("With sender_upi in records:")
print("  total_prior_transactions:", fixed_profile.total_prior_transactions)
print(f"  avg_amount: ₹{fixed_profile.avg_amount:.2f}")
print(f"  std_amount: ₹{fixed_profile.std_amount:.2f}")
print(f"  daily_frequency_mean: {fixed_profile.daily_frequency_mean:.2f}")
print("  known_devices:", fixed_profile.known_devices)
print("  known_recipients count:", len(fixed_profile.known_recipients))
