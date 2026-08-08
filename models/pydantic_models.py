from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    message_id: str
    thread_id: str
    sender: str
    subject: str
    date_received: str
    snippet: str
    body: str
    content_hash: str


class PlacementEmailExtraction(BaseModel):
    company: str = Field(default="", description="Name of the hiring or interviewing company")
    event_type: str = Field(default="", description="Type of event: e.g. Internship, Full-time, Coding test, OA, Interview, PPT")
    deadline: str = Field(default="", description="ISO timestamp or plain text deadline date/time")
    deadline_exists: bool = Field(default=False, description="True if an explicit deadline or interview date exists")
    action_required: bool = Field(default=False, description="True if user must submit, register, attend, or act")
    priority: str = Field(default="Medium", description="Priority level: High, Medium, or Low")
    registration_link: str = Field(default="", description="URL link for registration, assessment, or form")
    eligibility: str = Field(default="", description="Eligible branches, CGPA, graduation batch details")
    summary: str = Field(default="", description="2-3 sentence overview of the email contents and next steps")
    confidence: float = Field(default=0.0, description="Extraction confidence score from 0.0 to 1.0")


class ClassificationResult(BaseModel):
    is_placement_related: bool
    reason: str
    category: str  # e.g., PLACEMENT, SPAM, NEWSLETTER, PERSONAL, PROMOTION


class DecisionResult(BaseModel):
    should_create_task: bool
    should_update_task: bool
    existing_task_id: Optional[str] = None
    reason: str
    extraction: PlacementEmailExtraction


class TaskPayload(BaseModel):
    google_task_id: Optional[str] = None
    company: str
    event_type: str
    task_title: str
    due_date: Optional[str] = None
    priority: str
    registration_link: str
    eligibility: str
    summary: str
    email_subject: str
    notes: str


class ProcessingStatusResponse(BaseModel):
    message_id: str
    status: str
    company: str
    action_taken: str
    timestamp: datetime
