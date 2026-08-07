import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st

from config.settings import settings
from database.connection import SessionLocal, init_db
from database.models import EmailRecord, TaskRecord, ProcessedEmailRecord
from services.orchestrator import PipelineOrchestrator
from utils.logger import LOG_FILE

st.set_page_config(
    page_title="Placement Email AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern aesthetic
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #1E88E5 0%, #7B1FA2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #6c757d;
        font-size: 1rem;
        margin-bottom: 25px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 18px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        text-align: center;
        border-left: 5px solid #1E88E5;
    }
    .priority-high {
        background-color: #ffebee;
        color: #c62828;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .priority-medium {
        background-color: #fff8e1;
        color: #f57f17;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
    .priority-low {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize DB
init_db()


def get_db_session():
    return SessionLocal()


def load_metrics(db):
    total_emails = db.query(EmailRecord).count()
    tasks_created = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "CREATED_TASK").count()
    tasks_updated = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "UPDATED_TASK").count()
    emails_ignored = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.processing_status == "IGNORED").count()
    return total_emails, tasks_created, tasks_updated, emails_ignored


# Sidebar
st.sidebar.title("🤖 Agent Settings")
st.sidebar.markdown("---")
st.sidebar.subheader("System Status")
st.sidebar.success("🟢 Active & Monitoring")
st.sidebar.info(f"**Groq Model:** `{settings.GROQ_MODEL}`")
st.sidebar.info(f"**Check Interval:** `{settings.CHECK_INTERVAL}s`")

if st.sidebar.button("🔄 Trigger Sync Now", type="primary", use_container_width=True):
    with st.spinner("Processing unread emails with Groq LLM agent..."):
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run_pipeline()
        st.session_state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.success(f"Sync complete! Created: {result.get('tasks_created')}, Updated: {result.get('tasks_updated')}")
        st.rerun()

last_sync = st.session_state.get("last_sync", "Never (Run Sync to start)")
st.sidebar.markdown(f"**Last Sync:** `{last_sync}`")

# Header Section
st.markdown('<p class="main-title">Placement Email AI Task Automation Agent</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Autonomous email intelligence, extraction, and Google Tasks sync powered by Groq LLM</p>', unsafe_allow_html=True)

db = get_db_session()

try:
    total_emails, tasks_created, tasks_updated, emails_ignored = load_metrics(db)

    # Top Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Emails Processed", total_emails)
    with col2:
        st.metric("Tasks Created", tasks_created, delta=f"+{tasks_created}" if tasks_created > 0 else None)
    with col3:
        st.metric("Tasks Updated", tasks_updated, delta=f"+{tasks_updated}" if tasks_updated > 0 else None)
    with col4:
        st.metric("Emails Ignored", emails_ignored)

    st.markdown("---")

    # Main Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📌 Upcoming Tasks & Deadlines", "📧 Processed Emails & Extracted Data", "🔄 Reprocess Emails", "📜 System Processing Logs"])

    # Tab 1: Tasks
    with tab1:
        st.subheader("Google Tasks & Placement Deadlines")
        tasks = db.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()

        if not tasks:
            st.info("No active placement tasks created yet. Trigger a sync or check your inbox.")
        else:
            task_data = []
            for t in tasks:
                p_class = "priority-medium"
                if t.priority and t.priority.lower() == "high":
                    p_class = "priority-high"
                elif t.priority and t.priority.lower() == "low":
                    p_class = "priority-low"

                task_data.append({
                    "Google Task ID": t.google_task_id or "N/A",
                    "Company": t.company,
                    "Event Type": t.event_type,
                    "Deadline": t.deadline or "N/A",
                    "Priority": t.priority,
                    "Registration Link": t.registration_link or "N/A",
                    "Summary": t.summary,
                    "Created At": t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "N/A"
                })

            df_tasks = pd.DataFrame(task_data)
            st.dataframe(df_tasks, use_container_width=True)

            st.markdown("### 📋 Task Details")
            for t in tasks:
                with st.expander(f"🏢 {t.company} - {t.event_type} | Deadline: {t.deadline or 'N/A'}"):
                    st.markdown(f"**Priority:** {t.priority}")
                    st.markdown(f"**Eligibility Criteria:** {t.eligibility or 'N/A'}")
                    st.markdown(f"**Registration URL:** [{t.registration_link}]({t.registration_link})" if t.registration_link and t.registration_link.startswith("http") else f"**Registration Link:** {t.registration_link}")
                    st.markdown(f"**Summary:** {t.summary}")

    # Tab 2: Processed Emails
    with tab2:
        st.subheader("Search & View Processed Emails")
        search_query = st.text_input("🔍 Search by Company, Subject, or Message ID:", "")

        query = db.query(EmailRecord)
        if search_query:
            query = query.filter(
                (EmailRecord.subject.ilike(f"%{search_query}%")) |
                (EmailRecord.sender.ilike(f"%{search_query}%")) |
                (EmailRecord.message_id.ilike(f"%{search_query}%"))
            )
        emails = query.order_by(EmailRecord.timestamp.desc()).all()

        if not emails:
            st.warning("No processed emails found matching search criteria.")
        else:
            for e in emails:
                proc = db.query(ProcessedEmailRecord).filter(ProcessedEmailRecord.message_id == e.message_id).first()
                status_color = "🟢" if e.processing_status in ["CREATED_TASK", "UPDATED_TASK"] else "🔴"

                with st.expander(f"{status_color} [{e.processing_status}] {e.subject} (From: {e.sender})"):
                    st.write(f"**Message ID:** `{e.message_id}` | **Received:** `{e.date_received}`")
                    st.write(f"**Is Placement Related:** `{e.is_placement_related}`")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown("**Original Email Body:**")
                        st.text_area("Body", e.body, height=180, key=f"body_{e.message_id}")

                    with col_b:
                        st.markdown("**Extracted JSON Output:**")
                        if proc and proc.extracted_json:
                            try:
                                json_obj = json.loads(proc.extracted_json)
                                st.json(json_obj)
                            except Exception:
                                st.text(proc.extracted_json)
                        else:
                            st.info("No LLM extraction performed (Filtered out as non-placement).")

    # Tab 3: Manual Reprocess
    with tab3:
        st.subheader("Manual Email Reprocessing")
        st.write("Trigger full re-extraction and decision engine for a specific email.")

        unprocessed = db.query(EmailRecord).all()
        email_options = {f"{e.message_id} - {e.subject}": e.message_id for e in unprocessed}

        if not email_options:
            st.info("No email records available in DB to reprocess.")
        else:
            selected_email_str = st.selectbox("Select Email to Reprocess:", list(email_options.keys()))
            selected_msg_id = email_options[selected_email_str]

            if st.button("🚀 Reprocess Email Now", type="primary"):
                with st.spinner(f"Reprocessing message {selected_msg_id}..."):
                    orchestrator = PipelineOrchestrator()
                    success = orchestrator.reprocess_email_by_id(selected_msg_id)
                    if success:
                        st.success(f"Email `{selected_msg_id}` successfully reprocessed!")
                        st.rerun()
                    else:
                        st.error("Failed to reprocess email.")

    # Tab 4: Logs
    with tab4:
        st.subheader("Structured Processing Logs")

        if LOG_FILE.exists():
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                log_contents = f.readlines()

            log_filter = st.text_input("Filter logs:", "")
            filtered_logs = [line for line in log_contents if log_filter.lower() in line.lower()] if log_filter else log_contents

            st.text_area("Log Output", "".join(filtered_logs[-150:]), height=350)

            st.download_button(
                label="📥 Export Full Logs File",
                data="".join(log_contents),
                file_name="placement_agent_logs.txt",
                mime="text/plain"
            )
        else:
            st.info("Log file has not been created yet.")

finally:
    db.close()
