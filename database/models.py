from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from database.connection import Base


class EmailRecord(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(String(255), unique=True, index=True, nullable=False)
    thread_id = Column(String(255), index=True, nullable=True)
    sender = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    date_received = Column(String(255), nullable=True)
    snippet = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    content_hash = Column(String(64), index=True, nullable=False)
    is_placement_related = Column(Boolean, default=False)
    processing_status = Column(String(50), default="UNPROCESSED")  # UNPROCESSED, IGNORED, PROCESSED, ERROR
    timestamp = Column(DateTime, default=datetime.utcnow)

    processed_record = relationship("ProcessedEmailRecord", back_populates="email", uselist=False)


class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    google_task_id = Column(String(255), unique=True, index=True, nullable=True)
    company = Column(String(255), index=True, nullable=False)
    event_type = Column(String(100), nullable=True)
    task_title = Column(String(500), nullable=False)
    deadline = Column(String(255), nullable=True)
    priority = Column(String(50), default="Medium")
    registration_link = Column(Text, nullable=True)
    eligibility = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String(50), default="NEEDS_ACTION")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    processed_records = relationship(
        "ProcessedEmailRecord",
        foreign_keys="[ProcessedEmailRecord.task_id]",
        primaryjoin="TaskRecord.google_task_id == ProcessedEmailRecord.task_id",
        back_populates="task"
    )


class ProcessedEmailRecord(Base):
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(String(255), ForeignKey("emails.message_id"), index=True, nullable=False)
    thread_id = Column(String(255), nullable=True)
    task_id = Column(String(255), ForeignKey("tasks.google_task_id"), index=True, nullable=True)
    company = Column(String(255), nullable=True)
    deadline = Column(String(255), nullable=True)
    content_hash = Column(String(64), index=True, nullable=False)
    processing_status = Column(String(50), nullable=False)  # IGNORED, CREATED_TASK, UPDATED_TASK, ERROR
    extracted_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    email = relationship("EmailRecord", back_populates="processed_record")
    task = relationship(
        "TaskRecord",
        foreign_keys=[task_id],
        primaryjoin="ProcessedEmailRecord.task_id == TaskRecord.google_task_id",
        back_populates="processed_records"
    )
