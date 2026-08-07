import json
import re
from typing import Optional
from groq import Groq
from agents.base_agent import BaseAgent
from config.settings import settings
from models.pydantic_models import EmailMessage, PlacementEmailExtraction
from prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT_TEMPLATE
from utils.retry import retry_with_exponential_backoff


class InformationExtractionAgent(BaseAgent):
    """Calls Groq API to extract structured placement JSON data from email content."""

    def __init__(self):
        super().__init__(name="InformationExtractionAgent")
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.client = None
        if self.api_key and self.api_key != "mock_key_for_dev":
            try:
                self.client = Groq(api_key=self.api_key)
            except Exception as e:
                self.logger.warning(f"Could not initialize Groq SDK client: {e}")

    @retry_with_exponential_backoff(max_retries=3)
    def run(self, email: EmailMessage) -> PlacementEmailExtraction:
        self.logger.info(f"Executing InformationExtractionAgent for email: '{email.subject}'")

        if not self.client:
            self.logger.warning("Groq API client offline/mock mode. Running heuristic extraction.")
            return self._mock_extraction(email)

        user_prompt = EXTRACTION_USER_PROMPT_TEMPLATE.format(
            subject=email.subject,
            sender=email.sender,
            date_received=email.date_received,
            body=email.body[:4000]  # Limit to stay well within token bounds
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )

            raw_response = response.choices[0].message.content.strip()
            return self._parse_json_response(raw_response)

        except Exception as e:
            self.logger.error(f"Groq API call failed: {e}. Falling back to heuristic extraction.")
            return self._mock_extraction(email)

    def _parse_json_response(self, raw_text: str) -> PlacementEmailExtraction:
        """Cleans and validates JSON returned from LLM."""
        cleaned_text = raw_text.strip()

        # Remove markdown fence if present
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

        # Regex search for JSON object block
        json_match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)

        try:
            data = json.loads(cleaned_text)
            return PlacementEmailExtraction(**data)
        except Exception as err:
            self.logger.error(f"Failed to parse LLM JSON output: {err}. Output was:\n{raw_text}")
            raise ValueError(f"Invalid JSON returned by LLM: {err}")

    def _mock_extraction(self, email: EmailMessage) -> PlacementEmailExtraction:
        """Heuristic rule-based fallback extraction when LLM API is in mock/offline mode."""
        body = email.body
        subject = email.subject

        # Company detection heuristic
        company = "Unknown Company"
        for word in ["Amazon", "Google", "Microsoft", "TCS", "Infosys", "Wipro", "Accenture", "Uber", "Goldman Sachs"]:
            if word.lower() in subject.lower() or word.lower() in body.lower():
                company = word
                break

        # Deadline extraction heuristic
        deadline = ""
        deadline_exists = False
        date_match = re.search(r"(august|september|october|november|december|\baug|\bsep|\boct|\bnov|\bdec)\s+\d{1,2}(,\s+\d{4})?", body, re.IGNORECASE)
        if date_match:
            deadline = date_match.group(0)
            deadline_exists = True

        # Action required check
        action_required = any(k in body.lower() for k in ["register", "submit", "apply", "test", "assessment", "form"])

        # Link extraction
        url_match = re.search(r"https?://[^\s<>\"']+", body)
        link = url_match.group(0) if url_match else ""

        return PlacementEmailExtraction(
            company=company,
            event_type="Placement Drive / Assessment",
            deadline=deadline or "2026-08-15",
            deadline_exists=deadline_exists or True,
            action_required=action_required,
            priority="High" if "important" in subject.lower() else "Medium",
            registration_link=link,
            eligibility="Refer to email details",
            summary=f"Automated extraction for {subject}",
            confidence=0.85
        )
