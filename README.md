# 🤖 AI Placement Email Task Automation Agent

An autonomous production-grade AI agent that continuously monitors your Gmail inbox, intelligently filters and understands placement-related emails (internships, online assessments, hiring drives, pre-placement talks, and interview schedules) using the **Groq LLM API**, extracts deadlines and key details into structured JSON, and automatically creates or updates tasks in **Google Tasks** to eliminate manual tracking.

---

## 🌟 Primary Features & Workflow

1. **Gmail OAuth2 Authentication**: Securely connects to your Gmail inbox via official Google APIs.
2. **Fast Filtering Engine**: Filters out newsletters, advertisements, marketing promotions, and personal emails before making LLM calls to preserve performance and token limits.
3. **Structured Groq LLM Extraction**: Sends relevant placement email content to Groq LLM (`llama-3.3-70b-versatile` or configured model) and extracts structured JSON containing:
   - `company`
   - `event_type`
   - `deadline`
   - `deadline_exists`
   - `action_required`
   - `priority`
   - `registration_link`
   - `eligibility`
   - `summary`
   - `confidence`
4. **Autonomous Decision Engine**:
   - Only creates/updates tasks if `deadline_exists == true` AND `action_required == true`.
5. **Smart Duplicate Prevention**:
   - Uses SHA256 content hashing in SQLite to prevent duplicate processing.
   - Searches existing Google Tasks to update deadlines (e.g. "Deadline Extended" emails) instead of creating duplicate tasks.
6. **SQLite Local Database**: Tracks processed emails, content hashes, and created task IDs.
7. **Streamlit UI Dashboard**: Real-time analytics, task listing with color-coded priorities, searchable processed email table, extracted JSON viewer, manual reprocess trigger, and interactive log exporter.
8. **Structured Logging & Resilience**: Exponential backoff retries on network and LLM API calls with fault isolation.

---

## 📁 Project Architecture

```
Placement Email AI Agent/
├── .env.example              # Environment variables template
├── README.md                 # Complete documentation
├── requirements.txt          # Python dependencies
├── main.py                   # Central CLI & daemon launcher
├── config/
│   └── settings.py           # Pydantic environment configuration
├── database/
│   ├── connection.py         # SQLAlchemy SQLite engine & session management
│   └── models.py             # Database models (emails, tasks, processed_emails)
├── models/
│   └── pydantic_models.py    # Strict Pydantic data schemas
├── prompts/
│   ├── classification_prompt.py  # LLM classification template
│   └── extraction_prompt.py      # Groq LLM JSON extraction prompt
├── gmail/
│   ├── auth.py               # Google OAuth2 credential manager
│   └── client.py             # Gmail API fetcher & MIME body parser
├── tasks/
│   └── client.py             # Google Tasks API manager (search, insert, patch)
├── agents/
│   ├── base_agent.py         # Abstract base agent interface
│   ├── email_fetch_agent.py  # Unread email fetch agent
│   ├── classification_agent.py # Rule-based & keyword filter agent
│   ├── extraction_agent.py  # Groq API structured JSON extraction agent
│   ├── decision_agent.py    # Business rules & duplicate detection engine
│   └── task_agent.py        # Task creation/update agent
├── services/
│   ├── orchestrator.py       # End-to-end multi-agent pipeline orchestrator
│   └── scheduler.py          # APScheduler background periodic check daemon
├── utils/
│   ├── logger.py             # Structured console & file logging
│   ├── hashing.py            # SHA256 content hash generator
│   └── retry.py              # Exponential backoff decorator
├── app/
│   ├── api.py                # FastAPI REST endpoints
│   └── dashboard.py          # Streamlit UI dashboard
└── tests/
    └── test_agents.py        # Unit tests for agents & decision logic
```

---

## ⚡ Quick Start & Installation

### 1. Clone & Setup Environment

```bash
cd "d:/project/Placement Email AI Agent"
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Update your credentials:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/

DATABASE_URL=sqlite:///./placement_agent.db
CHECK_INTERVAL=300
ENABLE_DRY_RUN=False
```

### 3. Setting Up Google OAuth (Gmail & Tasks API)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable **Gmail API** and **Google Tasks API** under *APIs & Services > Library*.
4. Configure **OAuth Consent Screen** (Desktop App).
5. Go to *Credentials > Create Credentials > OAuth client ID*, choose **Desktop App**, download `client_secret.json` and save it as `credentials.json` in the root folder.

---

## 🚀 Running the Application

### 1. Default Mode (Sync & Continuous Background Daemon)

To execute an initial sync and start monitoring Gmail every 5 minutes:

```bash
python main.py
```

### 2. Launch Streamlit Monitoring Dashboard

To open the visual dashboard in your browser:

```bash
python main.py --dashboard
# Or directly:
streamlit run app/dashboard.py
```

### 3. Dry-Run / Development Mode (No Google Credentials Needed)

To test the multi-agent pipeline using mock placement emails:

```bash
python main.py --dry-run
```

### 4. Run Unit Tests

```bash
pytest tests/
```

### 5. Launch FastAPI REST Server

```bash
python main.py --api
```

---

## 📊 Streamlit Dashboard Overview

The dashboard includes:
- **Metrics Cards**: Total processed emails, tasks created, tasks updated, ignored emails.
- **Upcoming Placement Deadlines**: Color-coded priorities (**HIGH: Red**, **MEDIUM: Orange**, **LOW: Green**) with registration links and summaries.
- **Searchable Processed Email Log**: View extracted JSON schema side-by-side with original email body.
- **Manual Reprocessing**: Trigger instant re-extraction for any message ID.
- **Log Viewer & Exporter**: Inspect live structured logs and download log files.

---

## 🛡️ License & Principles
Built following clean architecture and SOLID design principles for high reliability, fault isolation, and autonomous task automation.
