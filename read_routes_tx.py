with open('backend/api/routes_transactions.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('/transactions/{transaction_id}')
print(text[idx-40:idx+800])
