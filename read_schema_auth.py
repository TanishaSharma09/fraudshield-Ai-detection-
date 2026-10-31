with open('backend/schemas/auth.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class AppUserUpdate')
print(text[idx:idx+600])
