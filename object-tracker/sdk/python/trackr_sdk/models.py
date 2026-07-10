from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Job(BaseModel):
    id: str
    filename: str
    status: JobStatus
    progress: float
    stage: str
    start_time: datetime
    completion_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    output_path: Optional[str] = None
    analytics: Optional[Dict[str, Any]] = None
    average_fps: Optional[float] = None
    processing_throughput: Optional[float] = None
    project_id: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    owner_id: str

class Token(BaseModel):
    access_token: str
    token_type: str
