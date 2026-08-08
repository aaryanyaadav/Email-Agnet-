import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import EmailRecord, TaskRecord
from models.pydantic_models import EmailMessage, PlacementEmailExtraction
from agents.classification_agent import EmailClassificationAgent
from agents.decision_agent import DecisionAgent
from utils.hashing import generate_email_hash


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_email_hashing():
    hash1 = generate_email_hash("Amazon Test", "tpo@college.edu", "Body text")
    hash2 = generate_email_hash("Amazon Test", "tpo@college.edu", "Body text")
    hash3 = generate_email_hash("Google STEP", "recruiter@google.com", "Different body")

    assert hash1 == hash2
    assert hash1 != hash3


def test_classification_agent():
    agent = EmailClassificationAgent()

    placement_email = EmailMessage(
        message_id="m1",
        thread_id="t1",
        sender="tpo@college.edu",
        subject="Important: Microsoft SDE Hiring Online Assessment",
        date_received="2026-08-06",
        snippet="Please register for Microsoft OA",
        body="Microsoft placement drive online assessment deadline August 10.",
        content_hash="h1"
    )

    spam_email = EmailMessage(
        message_id="m2",
        thread_id="t2",
        sender="promo@brand.com",
        subject="50% Discount on Shoes - Flash Sale Newsletter",
        date_received="2026-08-06",
        snippet="Unsubscribe anytime",
        body="Buy shoes now with code FLASH50. Newsletter subscription.",
        content_hash="h2"
    )

    res1 = agent.run(placement_email)
    res2 = agent.run(spam_email)

    assert res1.is_placement_related is True
    assert res2.is_placement_related is False


def test_decision_agent_logic(db_session):
    decision_agent = DecisionAgent()

    email = EmailMessage(
        message_id="m3",
        thread_id="t3",
        sender="recruitment@uber.com",
        subject="Uber SDE Internship Assessment Link",
        date_received="2026-08-06",
        snippet="Uber OA",
        body="Complete Uber test by Aug 12.",
        content_hash="h3"
    )

    # 1. Test when deadline_exists=True AND action_required=True -> CREATE TASK
    ext_valid = PlacementEmailExtraction(
        company="Uber",
        event_type="Internship Assessment",
        deadline="2026-08-12",
        deadline_exists=True,
        action_required=True,
        priority="High",
        registration_link="https://uber.com/test",
        eligibility="CGPA >= 8.0",
        summary="Complete Uber test",
        confidence=0.9
    )
    dec1 = decision_agent.run(email, ext_valid, db_session)
    assert dec1.should_create_task is True

    # 2. Test when deadline_exists=False -> IGNORE EMAIL
    ext_no_deadline = PlacementEmailExtraction(
        company="Uber",
        event_type="Pre-placement Info",
        deadline="",
        deadline_exists=False,
        action_required=True,
        confidence=0.8
    )
    dec2 = decision_agent.run(email, ext_no_deadline, db_session)
    assert dec2.should_create_task is False
    assert dec2.should_update_task is False
