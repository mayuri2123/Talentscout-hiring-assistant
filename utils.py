import re
from typing import Optional, Dict
from cryptography.fernet import Fernet
import os

# -----------------------------
# Regex patterns (precompiled for speed)
# -----------------------------
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\d{10,})")
EXPERIENCE_PATTERN = re.compile(r"(\d+(\.\d+)?)\s*(?:years|yrs|year)?", re.IGNORECASE)

# -----------------------------
# Extraction Functions
# -----------------------------
def extract_email(text: str) -> Optional[str]:
    """Extract first valid email from text."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None

def extract_phone(text: str) -> Optional[str]:
    """Extract first valid phone number (10+ digits)."""
    match = PHONE_PATTERN.search(text)
    if match:
        num = re.sub(r"[^\d+]", "", match.group(0))
        if len(num) >= 10:
            return num
    return None

def extract_experience(text: str) -> Optional[float]:
    """Extract years of experience (supports '2', '2.5', '2 years', etc.)."""
    match = EXPERIENCE_PATTERN.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

# -----------------------------
# Field Handling
# -----------------------------
def next_missing_field(c: Dict) -> Optional[str]:
    """Return the next missing candidate field (order matters)."""
    order = ["full_name", "email", "phone", "experience", "position", "location", "tech_stack"]
    for f in order:
        if not c.get(f):
            return f
    return None

def detect_exit(text: str) -> bool:
    """Check if text is an exit command."""
    exit_words = ["exit", "quit", "stop", "bye", "goodbye", "end"]
    return text.strip().lower() in exit_words

# -----------------------------
# Secure Storage (Encryption)
# -----------------------------
def secure_store(data: dict) -> dict:
    """Encrypt sensitive fields if ENABLE_ENCRYPTION is set."""
    if not os.getenv("ENABLE_ENCRYPTION", "").lower() == "true":
        return data

    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("Encryption enabled but no ENCRYPTION_KEY provided.")

    f = Fernet(key.encode())
    stored = data.copy()
    for field in ["email", "phone"]:
        if stored.get(field):
            stored[field] = f.encrypt(stored[field].encode()).decode()
    return stored

# -----------------------------
# Safe Display (for UI)
# -----------------------------
def safe_display(value: Optional[str]) -> str:
    """Return value if present, else '⚠️ Missing'."""
    return value if value else "⚠️ Missing"
