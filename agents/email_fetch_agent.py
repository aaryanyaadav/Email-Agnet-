from typing import List
from agents.base_agent import BaseAgent
from gmail.client import GmailClient
from models.pydantic_models import EmailMessage


class EmailFetchAgent(BaseAgent):
    """Agent responsible for fetching unread messages from Gmail."""

    def __init__(self, gmail_client: GmailClient = None):
        super().__init__(name="EmailFetchAgent")
        self.gmail_client = gmail_client or GmailClient()

    def run(self, max_results: int = 20) -> List[EmailMessage]:
        self.logger.info("Executing EmailFetchAgent: Fetching unread emails...")
        messages = self.gmail_client.fetch_unread_messages(max_results=max_results)
        self.logger.info(f"EmailFetchAgent retrieved {len(messages)} email(s).")
        return messages
