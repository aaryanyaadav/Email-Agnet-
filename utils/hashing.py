import hashlib


def generate_email_hash(subject: str, sender: str, body: str) -> str:
    """Generates a unique SHA256 hash for email contents to prevent duplicate processing."""
    raw_payload = f"{subject.strip().lower()}|{sender.strip().lower()}|{body.strip()}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
