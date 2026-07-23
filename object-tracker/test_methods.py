import api.main as main
for r in main.app.routes:
    if 'google' in r.path:
        print(f"Path: {r.path}, Methods: {getattr(r, 'methods', 'No methods')}")
