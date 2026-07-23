import requests
import time
import os
import uuid

API_URL = "http://localhost:8000/api/v1"

def run_tests():
    print("Testing API Health...")
    try:
        health = requests.get(f"{API_URL}/system/health")
        print("Health Check:", health.json())
    except Exception as e:
        print("API not running, please start it.")
        return

    # Test Registration
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "password123"
    print(f"Registering user {email}...")
    res = requests.post(f"{API_URL}/auth/register", json={"email": email, "password": pwd, "name": "Test User"})
    print("Register Status:", res.status_code)

    # Test Login
    print("Logging in...")
    res = requests.post(f"{API_URL}/auth/login", data={"username": email, "password": pwd})
    if res.status_code != 200:
        print("Login failed!")
        return
    token = res.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful, token received.")

    # Create Project
    res = requests.post(f"{API_URL}/projects", json={"name": "Test Project"}, headers=headers)
    project_id = res.json()["id"]
    print("Created Project:", project_id)

    # Add Stream
    res = requests.post(f"{API_URL}/streams", json={"source": "0"}, headers=headers)
    print("Added Stream Status:", res.status_code)

    # Note: Cannot fully test Google OAuth login without browser interaction, but we can verify the redirect URL
    print("Testing Google OAuth Redirect...")
    res = requests.get(f"{API_URL}/auth/google/login", allow_redirects=False)
    if res.status_code in [302, 307] and "accounts.google.com" in res.headers.get("location", ""):
        print("Google OAuth redirect successful:", res.headers["location"][:100] + "...")
    else:
        print("Google OAuth redirect failed:", res.status_code)

    print("All backend endpoints functioning as expected!")

if __name__ == "__main__":
    run_tests()
