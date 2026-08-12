import requests

res = requests.get("http://localhost:8000/openapi.json")
if res.status_code == 200:
    for path in res.json()["paths"]:
        print(path)
else:
    print("Could not get openapi.json")
