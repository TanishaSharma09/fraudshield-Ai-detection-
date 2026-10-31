from ml_model.behavioural.baseline_tracker import get_baseline_tracker
from database.connection import query_all

tracker = get_baseline_tracker()
senders = query_all("SELECT DISTINCT sender_upi, COUNT(*) as cnt FROM transactions GROUP BY sender_upi ORDER BY cnt DESC LIMIT 5")
print("Top senders in transactions:")
for s in senders:
    profile = tracker.get_user_baseline_from_db(s["sender_upi"])
    print(f"Profile for {s['sender_upi']} (cnt: {s['cnt']}):")
    print(f"  total_prior_txs: {profile.total_prior_transactions}")
    print(f"  avg_amount: ₹{profile.avg_amount:.2f}")
    print(f"  std_amount: ₹{profile.std_amount:.2f}")
    print(f"  daily_frequency_mean: {profile.daily_frequency_mean:.2f}")
    print(f"  known_devices: {profile.known_devices}")
    print(f"  known_recipients: {len(profile.known_recipients)}")
