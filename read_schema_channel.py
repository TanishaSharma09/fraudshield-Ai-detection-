with open('backend/schemas/transaction.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('PaymentChannel =')
print(text[idx:idx+400])
