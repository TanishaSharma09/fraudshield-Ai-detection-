with open('backend/api/routes_alerts.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def list_alerts')
print(text[idx-40:idx+1500])
