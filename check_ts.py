from database.connection import query_all

rows = query_all("SELECT sender_upi, timestamp FROM transactions LIMIT 5")
for r in rows:
    print(dict(r))

print("\nCheck with LOWER(sender_upi):")
r2 = query_all("SELECT COUNT(*) as c FROM transactions WHERE LOWER(sender_upi) = 'arjun.sharma@okaxis'")
print(r2[0]['c'])

r3 = query_all("SELECT COUNT(*) as c FROM transactions WHERE sender_upi = 'arjun.sharma@okaxis'")
print("Exact match:", r3[0]['c'])

ts_sample = rows[0]['timestamp']
print("Sample timestamp:", ts_sample)

from datetime import datetime, timezone
now_iso = datetime.now(timezone.utc).isoformat()
print("now_iso:", now_iso)
r4 = query_all("SELECT COUNT(*) as c FROM transactions WHERE sender_upi = 'arjun.sharma@okaxis' AND timestamp < ?", (now_iso,))
print("Count < now_iso:", r4[0]['c'])
