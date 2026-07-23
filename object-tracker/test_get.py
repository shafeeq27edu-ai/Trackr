import requests

try:
    res = requests.get("http://localhost:8000/api/v1/auth/google/login", allow_redirects=False)
    print(f"Status: {res.status_code}")
    print(f"Headers: {res.headers}")
    print(f"Text: {res.text}")
except Exception as e:
    print(f"Error: {e}")
