with open('backend/services/alert_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def get_alerts')
print(text[idx:idx+1500])
