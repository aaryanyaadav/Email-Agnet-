import re
from agents.base_agent import BaseAgent
from models.pydantic_models import EmailMessage, ClassificationResult


class EmailClassificationAgent(BaseAgent):
    """Determines whether an email is placement/hiring/assessment related."""

    PLACEMENT_KEYWORDS = [
        "placement", "internship", "hiring", "recruitment", "online assessment",
        "coding test", "interview", "pre-placement talk", "ppt", "job offer",
        "campus drive", "resume submission", "application deadline", "shortlisted",
        "assessment link", "test schedule", "campus recruitment", "sde", "tpo"
    ]

    EXCLUDE_KEYWORDS = [
        "unsubscribe", "daily digest", "marketing", "promotion", "newsletter",
        "flash sale", "order receipt", "discount", "special offer", "social digest",
        "shopping", "subscription", "weekly summary", "blog post"
    ]

    def __init__(self):
        super().__init__(name="EmailClassificationAgent")

    def run(self, email: EmailMessage) -> ClassificationResult:
        self.logger.info(f"Executing EmailClassificationAgent for Msg ID: {email.message_id}")
        text_content = f"{email.subject} {email.snippet} {email.body}".lower()

        # Check explicit negative keywords first (marketing / newsletter / spam)
        for keyword in self.EXCLUDE_KEYWORDS:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_content):
                self.logger.info(
                    f"Email '{email.subject}' filtered out as SPAM/NEWSLETTER due to keyword: '{keyword}'"
                )
                return ClassificationResult(
                    is_placement_related=False,
                    reason=f"Matched exclude keyword: {keyword}",
                    category="NEWSLETTER"
                )

        # Check placement positive keywords
        matched_keywords = []
        for keyword in self.PLACEMENT_KEYWORDS:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_content):
                matched_keywords.append(keyword)

        if matched_keywords:
            self.logger.info(
                f"Email '{email.subject}' classified as PLACEMENT (Matched: {matched_keywords})"
            )
            return ClassificationResult(
                is_placement_related=True,
                reason=f"Matched placement keywords: {', '.join(matched_keywords)}",
                category="PLACEMENT"
            )

        self.logger.info(f"Email '{email.subject}' classified as NOT PLACEMENT related.")
        return ClassificationResult(
            is_placement_related=False,
            reason="No placement keywords detected.",
            category="PERSONAL"
        )
