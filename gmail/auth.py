import os
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from config.settings import settings
from utils.logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/tasks"
]


class GoogleAuthManager:
    """Manages Google OAuth2 credentials and service clients for Gmail & Google Tasks."""

    def __init__(self):
        self.credentials_path = settings.BASE_DIR / settings.GOOGLE_CREDENTIALS_FILE
        self.token_path = settings.BASE_DIR / settings.GOOGLE_TOKEN_FILE
        self._credentials: Optional[Credentials] = None

    def get_credentials(self) -> Optional[Credentials]:
        """Obtains valid OAuth2 credentials, refreshing or requesting approval as needed."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        if self.token_path.exists():
            try:
                self._credentials = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")

        if not self._credentials or not self._credentials.valid:
            if self._credentials and self._credentials.expired and self._credentials.refresh_token:
                try:
                    self._credentials.refresh(Request())
                    logger.info("Successfully refreshed Google OAuth credentials.")
                except Exception as e:
                    logger.error(f"Failed to refresh Google token: {e}")
                    self._credentials = None

            if not self._credentials and self.credentials_path.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    self._credentials = flow.run_local_server(port=0)
                    with open(self.token_path, "w") as token_file:
                        token_file.write(self._credentials.to_json())
                    logger.info("Successfully completed Google OAuth flow.")
                except Exception as e:
                    logger.error(f"Error completing OAuth flow: {e}")
                    self._credentials = None

        return self._credentials

    def get_gmail_service(self) -> Optional[Resource]:
        """Builds Gmail API client service."""
        creds = self.get_credentials()
        if not creds:
            logger.warning("No valid Google credentials available for Gmail API. Mock/Dry-run active.")
            return None
        return build("gmail", "v1", credentials=creds)

    def get_tasks_service(self) -> Optional[Resource]:
        """Builds Google Tasks API client service."""
        creds = self.get_credentials()
        if not creds:
            logger.warning("No valid Google credentials available for Tasks API. Mock/Dry-run active.")
            return None
        return build("tasks", "v1", credentials=creds)
