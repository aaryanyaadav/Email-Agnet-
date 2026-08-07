from typing import Optional
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from database.models import ProcessedEmailRecord, TaskRecord
from models.pydantic_models import PlacementEmailExtraction, DecisionResult, EmailMessage
from tasks.client import GoogleTasksClient


class DecisionAgent(BaseAgent):
    """Decision Engine implementing business logic and duplicate detection."""

    def __init__(self, tasks_client: Optional[GoogleTasksClient] = None):
        super().__init__(name="DecisionAgent")
        self.tasks_client = tasks_client or GoogleTasksClient()

    def run(self, email: EmailMessage, extraction: PlacementEmailExtraction, db: Session) -> DecisionResult:
        self.logger.info(f"Executing DecisionAgent for '{extraction.company}' (Msg ID: {email.message_id})")

        # Core Decision Logic Rule
        if not (extraction.deadline_exists and extraction.action_required):
            self.logger.info(
                f"Email '{email.subject}' ignored: deadline_exists={extraction.deadline_exists}, action_required={extraction.action_required}"
            )
            return DecisionResult(
                should_create_task=False,
                should_update_task=False,
                existing_task_id=None,
                reason="Does not meet criteria: requires both deadline_exists and action_required.",
                extraction=extraction
            )

        # 1. Check local DB processed_emails hash for exact message duplicate
        existing_processed = db.query(ProcessedEmailRecord).filter(
            ProcessedEmailRecord.content_hash == email.content_hash
        ).first()

        if existing_processed:
            self.logger.info(f"Email content hash {email.content_hash} already processed previously.")
            return DecisionResult(
                should_create_task=False,
                should_update_task=False,
                existing_task_id=existing_processed.task_id,
                reason="Duplicate content hash already processed.",
                extraction=extraction
            )

        # 2. Check local database tasks table for existing company/task
        existing_db_task = db.query(TaskRecord).filter(
            TaskRecord.company.ilike(f"%{extraction.company}%")
        ).first()

        if existing_db_task:
            self.logger.info(f"Existing local DB task found for '{extraction.company}' (ID: {existing_db_task.google_task_id})")
            return DecisionResult(
                should_create_task=False,
                should_update_task=True,
                existing_task_id=existing_db_task.google_task_id,
                reason=f"Existing task found in DB for company {extraction.company}. Triggering UPDATE.",
                extraction=extraction
            )

        # 3. Check Google Tasks API for similar active tasks
        similar_gtask = self.tasks_client.search_similar_task(
            company=extraction.company,
            title_keywords=extraction.event_type
        )

        if similar_gtask:
            g_id = similar_gtask.get("id")
            self.logger.info(f"Existing Google Task found for '{extraction.company}' (Google Task ID: {g_id})")
            return DecisionResult(
                should_create_task=False,
                should_update_task=True,
                existing_task_id=g_id,
                reason=f"Similar Google Task found (ID: {g_id}). Triggering UPDATE.",
                extraction=extraction
            )

        # 4. No duplicate found -> Create New Task
        self.logger.info(f"No duplicate found for '{extraction.company}'. Decision: CREATE NEW TASK.")
        return DecisionResult(
            should_create_task=True,
            should_update_task=False,
            existing_task_id=None,
            reason="Valid placement deadline with action required. New task creation.",
            extraction=extraction
        )
