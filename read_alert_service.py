with open('backend/services/alert_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def update_alert_action')
print(text[idx:idx+1500])
