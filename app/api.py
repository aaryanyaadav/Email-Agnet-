from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from database.models import EmailRecord, TaskRecord, ProcessedEmailRecord
from services.orchestrator import PipelineOrchestrator

app = FastAPI(
    title="Placement Email AI Agent API",
    description="REST API for controlling email automation agent, running manually triggered syncs, and retrieving tasks.",
    version="1.0.0"
)

orchestrator = PipelineOrchestrator()


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def read_root():
    return {"status": "online", "service": "Placement Email AI Agent"}


@app.post("/api/sync")
def trigger_sync():
    """Triggers an immediate email fetching and task extraction cycle."""
    try:
        metrics = orchestrator.run_pipeline()
        return {"message": "Sync cycle completed successfully.", "metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Retrieves overall processing metrics and statistics."""
    total_emails = db.query(EmailRecord).count()
    total_tasks = db.query(TaskRecord).count()
    tasks_created = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "CREATED_TASK").count()
    tasks_updated = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "UPDATED_TASK").count()
    emails_ignored = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "IGNORED").count()

    return {
        "total_emails_processed": total_emails,
        "tasks_count": total_tasks,
        "tasks_created": tasks_created,
        "tasks_updated": tasks_updated,
        "emails_ignored": emails_ignored
    }


@app.post("/api/reprocess/{message_id}")
def reprocess_email(message_id: str):
    """Manually reprocesses an email by its message ID."""
    success = orchestrator.reprocess_email_by_id(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Email message ID not found in database.")
    return {"message": f"Successfully reprocessed email {message_id}"}
