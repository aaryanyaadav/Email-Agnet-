import uuid
from typing import Dict, Any, Optional, List
from gmail.auth import GoogleAuthManager
from models.pydantic_models import TaskPayload
from utils.logger import logger
from utils.retry import retry_with_exponential_backoff


class GoogleTasksClient:
    """Interface for managing Google Tasks (Search, Create, Update)."""

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.service = self.auth_manager.get_tasks_service()
        self.default_tasklist_id = "@default"

    @retry_with_exponential_backoff(max_retries=3)
    def search_similar_task(self, company: str, title_keywords: str) -> Optional[Dict[str, Any]]:
        """Searches existing Google Tasks for matching company or event title."""
        if not self.service:
            logger.info(f"Google Tasks API offline. Search simulated for '{company}'.")
            return None

        try:
            tasks_result = self.service.tasks().list(
                tasklist=self.default_tasklist_id,
                showCompleted=False
            ).execute()
            items = tasks_result.get("items", [])

            search_query_comp = company.strip().lower()
            search_query_kw = title_keywords.strip().lower()

            for item in items:
                task_title = item.get("title", "").lower()
                task_notes = item.get("notes", "").lower()

                if search_query_comp and (search_query_comp in task_title or search_query_comp in task_notes):
                    logger.info(f"Found matching existing task in Google Tasks: '{item.get('title')}' (ID: {item.get('id')})")
                    return item

            return None
        except Exception as e:
            logger.error(f"Error searching Google Tasks: {e}")
            return None

    @retry_with_exponential_backoff(max_retries=3)
    def create_task(self, payload: TaskPayload) -> Dict[str, Any]:
        """Creates a new task in Google Tasks."""
        title = f"[{payload.priority.upper()}] {payload.company} - {payload.event_type}"
        notes = (
            f"Company: {payload.company}\n"
            f"Summary: {payload.summary}\n"
            f"Eligibility: {payload.eligibility}\n"
            f"Registration Link: {payload.registration_link}\n"
            f"Original Subject: {payload.email_subject}\n"
            f"Priority: {payload.priority}\n"
            f"Deadline: {payload.due_date}"
        )

        task_body = {
            "title": title,
            "notes": notes,
        }

        if payload.due_date and "T" in payload.due_date:
            task_body["due"] = payload.due_date

        if not self.service:
            mock_id = f"mock_gtask_{uuid.uuid4().hex[:8]}"
            logger.info(f"[DRY-RUN] Created Google Task '{title}' with Mock ID {mock_id}")
            return {"id": mock_id, "title": title, "notes": notes, "status": "needsAction"}

        try:
            created_task = self.service.tasks().insert(
                tasklist=self.default_tasklist_id,
                body=task_body
            ).execute()
            logger.info(f"Successfully created Google Task '{title}' (ID: {created_task.get('id')})")
            return created_task
        except Exception as e:
            logger.error(f"Failed to create Google Task: {e}")
            raise

    @retry_with_exponential_backoff(max_retries=3)
    def update_task(self, task_id: str, payload: TaskPayload) -> Dict[str, Any]:
        """Updates an existing Google Task with refreshed deadline, notes, or details."""
        title = f"[{payload.priority.upper()}] {payload.company} - {payload.event_type} (UPDATED)"
        notes = (
            f"Company: {payload.company}\n"
            f"Summary: {payload.summary}\n"
            f"Eligibility: {payload.eligibility}\n"
            f"Registration Link: {payload.registration_link}\n"
            f"Original Subject: {payload.email_subject}\n"
            f"Priority: {payload.priority}\n"
            f"Updated Deadline: {payload.due_date}"
        )

        task_body = {
            "id": task_id,
            "title": title,
            "notes": notes,
        }

        if payload.due_date and "T" in payload.due_date:
            task_body["due"] = payload.due_date

        if not self.service:
            logger.info(f"[DRY-RUN] Updated Google Task ID {task_id} with new deadline '{payload.due_date}'")
            return {"id": task_id, "title": title, "notes": notes, "status": "needsAction"}

        try:
            updated_task = self.service.tasks().patch(
                tasklist=self.default_tasklist_id,
                task=task_id,
                body=task_body
            ).execute()
            logger.info(f"Successfully updated Google Task ID '{task_id}'")
            return updated_task
        except Exception as e:
            logger.error(f"Failed to update Google Task {task_id}: {e}")
            raise
