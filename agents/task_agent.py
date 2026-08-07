import json
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from agents.base_agent import BaseAgent
from database.models import EmailRecord, TaskRecord, ProcessedEmailRecord
from models.pydantic_models import EmailMessage, DecisionResult, TaskPayload
from tasks.client import GoogleTasksClient


class TaskAgent(BaseAgent):
    """Executes Task creation/update on Google Tasks API and syncs with SQLite database."""

    def __init__(self, tasks_client: Optional[GoogleTasksClient] = None):
        super().__init__(name="TaskAgent")
        self.tasks_client = tasks_client or GoogleTasksClient()

    def run(self, email: EmailMessage, decision: DecisionResult, db: Session) -> Optional[TaskRecord]:
        self.logger.info(f"Executing TaskAgent for '{email.subject}'")

        extraction = decision.extraction
        payload = TaskPayload(
            company=extraction.company or "Placement Company",
            event_type=extraction.event_type or "Registration / Drive",
            task_title=f"{extraction.company} - {extraction.event_type}",
            due_date=extraction.deadline,
            priority=extraction.priority or "Medium",
            registration_link=extraction.registration_link or "N/A",
            eligibility=extraction.eligibility or "N/A",
            summary=extraction.summary or email.snippet,
            email_subject=email.subject,
            notes=f"Extracted from email: {email.subject}"
        )

        task_id = None
        action_taken = "IGNORED"

        if decision.should_create_task:
            gtask = self.tasks_client.create_task(payload)
            task_id = gtask.get("id")
            action_taken = "CREATED_TASK"

            # Create or update local task record in DB
            db_task = TaskRecord(
                google_task_id=task_id,
                company=payload.company,
                event_type=payload.event_type,
                task_title=payload.task_title,
                deadline=payload.due_date,
                priority=payload.priority,
                registration_link=payload.registration_link,
                eligibility=payload.eligibility,
                summary=payload.summary,
                status="NEEDS_ACTION"
            )
            db.add(db_task)
            db.commit()
            db.refresh(db_task)

        elif decision.should_update_task:
            task_id = decision.existing_task_id
            gtask = self.tasks_client.update_task(task_id, payload)
            action_taken = "UPDATED_TASK"

            # Update existing DB task
            db_task = db.query(TaskRecord).filter(
                TaskRecord.google_task_id == task_id
            ).first()
            if db_task:
                db_task.deadline = payload.due_date
                db_task.priority = payload.priority
                db_task.summary = payload.summary
                db_task.updated_at = datetime.utcnow()
                db.commit()

        # Update Email Record status
        email_rec = db.query(EmailRecord).filter(EmailRecord.message_id == email.message_id).first()
        if email_rec:
            email_rec.processing_status = action_taken
            email_rec.is_placement_related = True

        # Insert into ProcessedEmailRecord table
        processed_rec = ProcessedEmailRecord(
            message_id=email.message_id,
            thread_id=email.thread_id,
            task_id=task_id,
            company=extraction.company,
            deadline=extraction.deadline,
            content_hash=email.content_hash,
            processing_status=action_taken,
            extracted_json=extraction.model_dump_json()
        )
        db.add(processed_rec)
        db.commit()

        self.logger.info(f"TaskAgent completed execution. Action: {action_taken}, Task ID: {task_id}")
        return db_task if decision.should_create_task or decision.should_update_task else None
