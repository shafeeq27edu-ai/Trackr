import requests
from typing import List, Dict, Any, Optional
from trackr_sdk.models import Job, Project, Token

class TrackrClient:
    """REST Client for Trackr Platform"""
    
    def __init__(self, base_url: str = "http://localhost:8000", token: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def login(self, username: str, password: str) -> Token:
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password}
        )
        response.raise_for_status()
        token_data = response.json()
        token = Token(**token_data)
        self.session.headers.update({"Authorization": f"Bearer {token.access_token}"})
        return token

    # --- Jobs ---
    def list_jobs(self) -> List[Job]:
        response = self.session.get(f"{self.base_url}/api/v1/jobs")
        response.raise_for_status()
        return [Job(**j) for j in response.json().get("jobs", [])]

    def get_job(self, job_id: str) -> Job:
        response = self.session.get(f"{self.base_url}/api/v1/jobs/{job_id}")
        response.raise_for_status()
        return Job(**response.json())

    def submit_job(self, filename: str, project_id: Optional[str] = None) -> Job:
        payload = {"filename": filename}
        if project_id:
            payload["project_id"] = project_id
            
        response = self.session.post(f"{self.base_url}/api/v1/jobs", json=payload)
        response.raise_for_status()
        return Job(**response.json())

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        response = self.session.delete(f"{self.base_url}/api/v1/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    # --- System ---
    def get_health(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/v1/system/health")
        response.raise_for_status()
        return response.json()

    def list_models(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/v1/models")
        response.raise_for_status()
        return response.json()

    def list_plugins(self) -> Dict[str, Any]:
        response = self.session.get(f"{self.base_url}/api/v1/plugins")
        response.raise_for_status()
        return response.json()
