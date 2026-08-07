import base64
import re
from typing import List, Dict, Any, Optional
from gmail.auth import GoogleAuthManager
from models.pydantic_models import EmailMessage
from utils.hashing import generate_email_hash
from utils.logger import logger
from utils.retry import retry_with_exponential_backoff


class GmailClient:
    """Interface for fetching and querying emails from Gmail API."""

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self.auth_manager = auth_manager or GoogleAuthManager()
        self.service = self.auth_manager.get_gmail_service()

    @retry_with_exponential_backoff(max_retries=3)
    def fetch_unread_messages(self, max_results: int = 20) -> List[EmailMessage]:
        """Fetches unread emails from Gmail inbox."""
        if not self.service:
            logger.info("Gmail service unavailable. Generating mock placement emails for dry-run/testing.")
            return self._generate_mock_emails()

        try:
            query = "is:unread"
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            messages = results.get("messages", [])

            email_messages: List[EmailMessage] = []
            for msg_meta in messages:
                msg_id = msg_meta["id"]
                full_msg = self.service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()

                parsed_email = self._parse_message(full_msg)
                if parsed_email:
                    email_messages.append(parsed_email)

            return email_messages
        except Exception as e:
            logger.error(f"Error fetching messages from Gmail API: {e}")
            return []

    def mark_as_read(self, message_id: str) -> bool:
        """Removes the UNREAD label from a message."""
        if not self.service:
            logger.info(f"[DRY-RUN] Marked message {message_id} as READ.")
            return True
        try:
            self.service.users().messages().batchModify(
                userId="me",
                body={"ids": [message_id], "removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.info(f"Marked Gmail message {message_id} as READ.")
            return True
        except Exception as e:
            logger.error(f"Failed to mark message {message_id} as read: {e}")
            return False

    def _parse_message(self, raw_msg: Dict[str, Any]) -> Optional[EmailMessage]:
        """Parses raw Gmail API response into clean EmailMessage data model."""
        try:
            msg_id = raw_msg.get("id", "")
            thread_id = raw_msg.get("threadId", "")
            snippet = raw_msg.get("snippet", "")
            headers = raw_msg.get("payload", {}).get("headers", [])

            header_dict = {h["name"].lower(): h["value"] for h in headers}
            subject = header_dict.get("subject", "No Subject")
            sender = header_dict.get("from", "Unknown Sender")
            date_received = header_dict.get("date", "")

            body = self._extract_body(raw_msg.get("payload", {}))
            if not body:
                body = snippet

            content_hash = generate_email_hash(subject, sender, body)

            return EmailMessage(
                message_id=msg_id,
                thread_id=thread_id,
                sender=sender,
                subject=subject,
                date_received=date_received,
                snippet=snippet,
                body=body,
                content_hash=content_hash
            )
        except Exception as e:
            logger.error(f"Failed to parse email message payload: {e}")
            return None

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extracts plain text content from MIME multipart email payload."""
        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                elif mime_type == "text/html" and not body and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    raw_html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    body += self._clean_html(raw_html)
                elif "parts" in part:
                    body += self._extract_body(part)
        elif "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        return body.strip()

    def _clean_html(self, html_text: str) -> str:
        """Strips HTML tags to retrieve raw plain text."""
        clean = re.compile("<.*?>")
        return re.sub(clean, "", html_text)

    def _generate_mock_emails(self) -> List[EmailMessage]:
        """Generates realistic placement test emails for local development & demonstration."""
        sample_emails = [
            {
                "id": "mock_msg_001",
                "threadId": "mock_thread_001",
                "sender": "placement@university.edu",
                "subject": "IMPORTANT: Amazon SDE Internship 2026 - Registration & Online Assessment",
                "date": "2026-08-06 10:00:00",
                "body": """Dear Students,

Amazon is visiting our campus for the 2026 SDE Summer Internship role.
Eligible Branches: B.Tech CSE, IT, ECE (CGPA >= 7.5).
Deadline to register: August 10, 2026 at 11:59 PM IST.
Action Required: Fill out the application form immediately at https://amazon.jobs/campus/register-2026.
Online Assessment scheduled for August 12, 2026.

Best regards,
Placement Cell"""
            },
            {
                "id": "mock_msg_002",
                "threadId": "mock_thread_002",
                "sender": "campus@google.com",
                "subject": "Google STEP Internship Deadline Extended to Aug 15",
                "date": "2026-08-06 12:30:00",
                "body": """Hello Applicants,

The application deadline for Google STEP Internship 2026 has been extended!
New Deadline: August 15, 2026 at 5:00 PM.
Please complete your application and resume submission at https://buildyourfuture.withgoogle.com/programs/step.

Regards,
Google Student Recruitment Team"""
            },
            {
                "id": "mock_msg_003",
                "threadId": "mock_thread_003",
                "sender": "newsletter@techcrunch.com",
                "subject": "TechCrunch Daily Digest: Top AI Startups in 2026",
                "date": "2026-08-06 14:00:00",
                "body": """Here are the top news in tech today: AI agents, quantum computing breakthroughs, and Silicon Valley investments."""
            }
        ]

        messages = []
        for e in sample_emails:
            c_hash = generate_email_hash(e["subject"], e["sender"], e["body"])
            messages.append(
                EmailMessage(
                    message_id=e["id"],
                    thread_id=e["threadId"],
                    sender=e["sender"],
                    subject=e["subject"],
                    date_received=e["date"],
                    snippet=e["body"][:100],
                    body=e["body"],
                    content_hash=c_hash
                )
            )
        return messages
