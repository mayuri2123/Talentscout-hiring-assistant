import os
import re
import json
from typing import Optional, Dict, Any

# Optional encryption via cryptography.Fernet if available and enabled
def _get_fernet():
    try:
        from cryptography.fernet import Fernet
    except Exception:
        return None
    key = os.getenv("ENCRYPTION_KEY")
    enabled = os.getenv("ENABLE_ENCRYPTION", "false").lower() == "true"
    if not enabled or not key:
        return None
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        return None

FERNET = _get_fernet()

def secure_store(candidate_dict: Dict[str, Any]) -> Dict[str, Any]:
    if not FERNET:
        return candidate_dict
    safe = candidate_dict.copy()
    for k in ("email","phone"):
        if safe.get(k):
            safe[k] = FERNET.encrypt(str(safe[k]).encode()).decode()
    return safe

def safe_display(value: Optional[str]) -> str:
    return str(value) if value not in (None, "", "None") else "⚠️ Missing"

def detect_exit(text: str) -> bool:
    text = text.strip().lower()
    exits = ["exit","quit","stop","bye","goodbye","end"]
    return any(x == text or x in text for x in exits)

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{7,}\d)")
EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", re.I)

def extract_email(text: str) -> Optional[str]:
    m = EMAIL_RE.search(text)
    return m.group(0) if m else None

def extract_phone(text: str) -> Optional[str]:
    m = PHONE_RE.search(text)
    return m.group(0) if m else None

def extract_experience(text: str) -> Optional[float]:
    # match patterns like "2", "2.5", "2 years"
    m = EXP_RE.search(text)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    # fallback: bare number like "2.5"
    t = text.strip()
    try:
        if any(c.isdigit() for c in t):
            # pick first float-like token
            for tok in re.findall(r"\d+(?:\.\d+)?", t):
                return float(tok)
    except Exception:
        return None
    return None

def next_missing_field(cand: Dict[str, Any]) -> Optional[str]:
    order = ["full_name","email","phone","experience","position","location","tech_stack"]
    for f in order:
        v = cand.get(f, None)
        if v in (None, "", "None") or (f == "experience" and v is None):
            return f
    return None
