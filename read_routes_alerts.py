with open('backend/api/routes_alerts.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('router.patch')
if idx == -1:
    idx = text.find('/{alert_id}')
print(text[idx-50:idx+2000])
