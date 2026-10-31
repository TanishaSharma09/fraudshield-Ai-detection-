from backend.main import app

schema = app.openapi()
paths = sorted(schema.get('paths', {}).keys())
print(f"Total API Endpoints: {len(paths)}")
for p in paths:
    methods = list(schema['paths'][p].keys())
    print(f"{','.join(methods).upper():<10} {p}")
