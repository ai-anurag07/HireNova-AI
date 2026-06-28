from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
import uuid

class A2AContext(BaseModel):
    master_resume_id: Optional[str] = None
    prior_task_ids: List[str] = []
    preferences: Dict[str, Any] = {}

class A2AParams(BaseModel):
    task_type: str
    user_id: str
    session_id: str
    payload: Dict[str, Any]
    context: A2AContext

class A2AMessage(BaseModel):
    jsonrpc: str = "2.0"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    method: str = "execute_task"
    params: A2AParams

class A2AResponseResult(BaseModel):
    status: str # "completed", "streaming", "failed", "pending"
    output: Dict[str, Any]
    artifacts: List[Dict[str, str]] = [] # e.g. [{"type": "pdf", "url": "..."}]
    next_actions: List[str] = []

class A2AResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[A2AResponseResult] = None
    error: Optional[Dict[str, Any]] = None