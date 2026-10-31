with open('backend/services/transaction_service.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('def get_transactions')
print(text[idx+500:idx+2000])
