from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import EmailRecord, ProcessedEmailRecord
from agents.email_fetch_agent import EmailFetchAgent
from agents.classification_agent import EmailClassificationAgent
from agents.extraction_agent import InformationExtractionAgent
from agents.decision_agent import DecisionAgent
from agents.task_agent import TaskAgent
from models.pydantic_models import EmailMessage
from utils.logger import logger


class PipelineOrchestrator:
    """Coordinates end-to-end multi-agent processing pipeline with fault isolation."""

    def __init__(self):
        self.fetch_agent = EmailFetchAgent()
        self.classification_agent = EmailClassificationAgent()
        self.extraction_agent = InformationExtractionAgent()
        self.decision_agent = DecisionAgent()
        self.task_agent = TaskAgent()

    def run_pipeline(self) -> Dict[str, Any]:
        """Runs the complete automation cycle over unread emails."""
        logger.info("Starting Placement Email AI Agent pipeline cycle...")
        db: Session = SessionLocal()
        metrics = {
            "emails_fetched": 0,
            "classified_placement": 0,
            "tasks_created": 0,
            "tasks_updated": 0,
            "emails_ignored": 0,
            "errors": 0,
            "start_time": datetime.utcnow().isoformat()
        }

        try:
            # 1. Fetch unread emails
            emails: List[EmailMessage] = self.fetch_agent.run()
            metrics["emails_fetched"] = len(emails)

            for email in emails:
                try:
                    self._process_single_email(email, db, metrics)
                except Exception as err:
                    logger.error(f"Error processing message {email.message_id}: {err}", exc_info=True)
                    metrics["errors"] += 1
                    # Ensure database rollbacks so next email can proceed
                    db.rollback()

        finally:
            db.close()

        logger.info(f"Pipeline cycle completed. Metrics: {metrics}")
        return metrics

    def _process_single_email(self, email: EmailMessage, db: Session, metrics: Dict[str, Any]):
        """Processes a single email message through all agents with database tracking."""
        # Save raw email record if not exists
        existing_email = db.query(EmailRecord).filter(EmailRecord.message_id == email.message_id).first()
        if not existing_email:
            existing_email = EmailRecord(
                message_id=email.message_id,
                thread_id=email.thread_id,
                sender=email.sender,
                subject=email.subject,
                date_received=email.date_received,
                snippet=email.snippet,
                body=email.body,
                content_hash=email.content_hash,
                processing_status="UNPROCESSED"
            )
            db.add(existing_email)
            db.commit()

        # Check deduplication hash in processed table
        already_processed = db.query(ProcessedEmailRecord).filter(
            ProcessedEmailRecord.content_hash == email.content_hash
        ).first()

        if already_processed:
            logger.info(f"Skipping duplicate email content hash: {email.content_hash}")
            metrics["emails_ignored"] += 1
            return

        # 2. Classification
        class_res = self.classification_agent.run(email)
        existing_email.is_placement_related = class_res.is_placement_related

        if not class_res.is_placement_related:
            existing_email.processing_status = "IGNORED"
            processed_rec = ProcessedEmailRecord(
                message_id=email.message_id,
                thread_id=email.thread_id,
                content_hash=email.content_hash,
                processing_status="IGNORED"
            )
            db.add(processed_rec)
            db.commit()
            metrics["emails_ignored"] += 1
            return

        metrics["classified_placement"] += 1

        # 3. Extraction (Groq LLM)
        extraction = self.extraction_agent.run(email)

        # 4. Decision Engine
        decision = self.decision_agent.run(email, extraction, db)

        # 5. Task Agent execution
        if decision.should_create_task:
            self.task_agent.run(email, decision, db)
            metrics["tasks_created"] += 1
        elif decision.should_update_task:
            self.task_agent.run(email, decision, db)
            metrics["tasks_updated"] += 1
        else:
            existing_email.processing_status = "IGNORED"
            processed_rec = ProcessedEmailRecord(
                message_id=email.message_id,
                thread_id=email.thread_id,
                company=extraction.company,
                content_hash=email.content_hash,
                processing_status="IGNORED",
                extracted_json=extraction.model_dump_json()
            )
            db.add(processed_rec)
            db.commit()
            metrics["emails_ignored"] += 1

        # Mark message read in Gmail if live
        self.fetch_agent.gmail_client.mark_as_read(email.message_id)

    def reprocess_email_by_id(self, message_id: str) -> bool:
        """Allows manual reprocessing of a specific email record from database."""
        db: Session = SessionLocal()
        try:
            rec = db.query(EmailRecord).filter(EmailRecord.message_id == message_id).first()
            if not rec:
                logger.warning(f"Reprocess failed: Email message {message_id} not found in DB.")
                return False

            email = EmailMessage(
                message_id=rec.message_id,
                thread_id=rec.thread_id or "",
                sender=rec.sender or "",
                subject=rec.subject or "",
                date_received=rec.date_received or "",
                snippet=rec.snippet or "",
                body=rec.body or "",
                content_hash=rec.content_hash
            )

            # Delete old processed record if exists to allow fresh re-run
            db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.message_id == message_id).delete()
            db.commit()

            dummy_metrics = {"emails_fetched": 1, "classified_placement": 0, "tasks_created": 0, "tasks_updated": 0, "emails_ignored": 0, "errors": 0}
            self._process_single_email(email, db, dummy_metrics)
            logger.info(f"Manual reprocess completed for email {message_id}.")
            return True
        finally:
            db.close()
