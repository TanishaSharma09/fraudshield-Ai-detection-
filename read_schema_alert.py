with open('backend/schemas/alert.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class AlertActionRequest')
print(text[idx:idx+800])
