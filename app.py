import os
import json
from datetime import datetime
from typing import Optional, List

import streamlit as st
from pydantic import BaseModel, EmailStr

# Local modules
from prompts import SYSTEM_PROMPT, TECH_QA_PROMPT
from llm import chat, LLMUnavailable
from utils import (
    extract_email, extract_phone, extract_experience, next_missing_field,
    detect_exit, secure_store, safe_display
)
from questions_bank import generate_fallback_questions

st.set_page_config(page_title="TalentScout - AI Hiring Assistant", page_icon="🧭", layout="wide")

# ------------- Simple rule-based sentiment (no external downloads) -------------
POS_WORDS = set("""great awesome good nice cool happy pleased delighted excellent wonderful love thanks thank you""".split())
NEG_WORDS = set("""bad sad upset angry frustrated terrible poor hate sorry issue problem""".split())

def rule_sentiment(text: str) -> str:
    tokens = [t.strip(".,!?;:").lower() for t in text.split()]
    pos = sum(1 for t in tokens if t in POS_WORDS)
    neg = sum(1 for t in tokens if t in NEG_WORDS)
    if pos - neg > 1: return "🙂"
    if neg - pos > 1: return "😕"
    return "😐"

# ------------- Language detect (graceful fallback) -------------
def detect_language(text: str) -> str:
    try:
        from langdetect import detect
        lang = detect(text)
        return lang or "en"
    except Exception:
        return "en"

# ------------- Data model -------------
class Candidate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    experience: Optional[float] = None
    position: Optional[str] = None
    location: Optional[str] = None
    tech_stack: Optional[str] = None

    def is_complete(self):
        return all([
            self.full_name, self.email, self.phone,
            self.experience is not None, self.position,
            self.location, self.tech_stack
        ])

# ------------- State -------------
if "candidate" not in st.session_state:
    st.session_state.candidate = Candidate()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "asked_tech_questions" not in st.session_state:
    st.session_state.asked_tech_questions = False
if "last_input" not in st.session_state:
    st.session_state.last_input = None
if "language" not in st.session_state:
    st.session_state.language = "en"

# ------------- Styles -------------
st.markdown("""<style>
[data-testid="stSidebar"]{
  background:#0b1f3a;color:#fff;
}
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] p,[data-testid="stSidebar"] li{color:#fff!important}
.main-header{background:linear-gradient(120deg,#2E86C1,#1B4F72);padding:24px 20px;border-radius:14px;text-align:center;color:#fff;margin-bottom:16px}
.tagline{font-size:15px;color:#eaf2f8;margin-top:-6px}
.card{background:#f7f9fb;border:1px solid #e5e8eb;border-radius:12px;padding:14px 16px}
.key{color:#2c3e50;font-weight:600}
.chat-wrap{height:460px;overflow-y:auto;border:1px solid #e5e8eb;border-radius:12px;background:#fbfcfd;padding:8px}
.bubble.assistant{background:#d6eaf8;color:#0b3750;border-radius:12px;padding:10px 12px;margin:6px;max-width:85%}
.bubble.user{background:#d1f2eb;color:#0b5044;border-radius:12px;padding:10px 12px;margin:6px;margin-left:auto;max-width:85%}
.stButton>button{background:#2E86C1;color:#fff;border-radius:10px;padding:8px 14px;border:0}
</style>
""", unsafe_allow_html=True)

# ------------- Sidebar -------------
with st.sidebar:
    st.markdown("## 💡 How to use")
    st.markdown("""- Type your responses in the chat box.
- You can answer multiple fields at once or one-by-one.
- Say **exit** to end the chat gracefully.

**Example input:**
- Name: John Doe
- Email: john@example.com
- Phone: +1 415 555 8899
- Experience: 2.5 years
- Position: Data Scientist
- Location: Bangalore
- Tech Stack: Python, Django, SQL
""")
    if st.session_state.candidate.is_complete():
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        path = f"data/candidate_{timestamp}.json"
        if st.button("💾 Save Profile Snapshot"):
            os.makedirs("data", exist_ok=True)
            stored = st.session_state.candidate.dict()
            stored = secure_store(stored)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(stored, f, indent=2)
            st.success(f"Profile saved to `{path}` (PII encrypted if enabled)")

# ------------- Header & Layout -------------
st.markdown("<div class='main-header'><h1>🧭 TalentScout — AI Hiring Assistant</h1><p class='tagline'>Collect candidate info and assess skills with tailored technical questions</p></div>", unsafe_allow_html=True)
left, right = st.columns([1, 2])

# ------------- Candidate summary -------------
with left:
    st.markdown("### 📝 Candidate Summary")
    c = st.session_state.candidate
    st.markdown(f"""    <div class='card'>
      <div><span class='key'>👤 Full Name:</span> {safe_display(c.full_name)}</div>
      <div><span class='key'>📧 Email:</span> {safe_display(c.email)}</div>
      <div><span class='key'>📱 Phone:</span> {safe_display(c.phone)}</div>
      <div><span class='key'>💼 Experience:</span> {safe_display(f"{c.experience} years" if c.experience is not None else None)}</div>
      <div><span class='key'>🎯 Position:</span> {safe_display(c.position)}</div>
      <div><span class='key'>📍 Location:</span> {safe_display(c.location)}</div>
      <div><span class='key'>🛠️ Tech Stack:</span> {safe_display(c.tech_stack)}</div>
    </div>
    """, unsafe_allow_html=True)

# ------------- Greeting -------------
def ensure_greeting():
    if not st.session_state.messages:
        greeting = ("Hello! I’m TalentScout, your AI hiring assistant. "
                    "I’ll collect your basic details (name, contact, experience, position, location, tech stack) "
                    "and then ask a few tailored technical questions. You can type 'exit' anytime to end.")
        st.session_state.messages.append({"role": "assistant", "content": greeting})
ensure_greeting()

# ------------- Heuristics -------------
def enrich_candidate_from_text(text: str):
    c = st.session_state.candidate
    email = extract_email(text)
    phone = extract_phone(text)
    exp = extract_experience(text)
    lower = text.lower()

    if email: c.email = email
    if phone: c.phone = phone
    if exp is not None: c.experience = exp

    if any(k in lower for k in ["engineer","developer","scientist","analyst","manager","intern"]):
        c.position = c.position or text

    if "tech stack" in lower or any(k in lower for k in ["python","java","sql","django","flask","react","node","pytorch","tensorflow","pandas","numpy","ml","machine learning"]):
        c.tech_stack = c.tech_stack or text

    if "location" in lower or any(k in lower for k in ["nagpur","pune","mumbai","delhi","bangalore","bengaluru","hyderabad","remote","india","usa","uk","europe"]):
        c.location = c.location or text

    # treat two-word text (without email/phone) as potential name
    if " " in text.strip() and not c.full_name and not email and not phone and len(text.split())<=5:
        c.full_name = text.strip().title()

def generate_tech_questions(tech_stack: str) -> List[str]:
    # Try LLM if available; otherwise fallback bank
    try:
        prompt = TECH_QA_PROMPT.format(tech_stack=tech_stack)
        msg = [{"role":"system","content": "You generate concise interview questions."},
               {"role":"user","content": prompt}]
        out = chat(system_prompt="", messages=msg, temperature=0.2, max_tokens=400)
        lines = [ln.strip(" -") for ln in out.strip().splitlines() if ln.strip()]
        qs = []
        for ln in lines:
            q = ln
            if ") " in q and q[0].isdigit(): q = q.split(") ",1)[-1]
            if ". " in q and q[0].isdigit(): q = q.split(". ",1)[-1]
            qs.append(q.strip())
        if not qs: raise ValueError("no parsed questions")
        return qs[:5]
    except Exception:
        return generate_fallback_questions(tech_stack, max_questions=5)

def ask_for_next_field():
    c = st.session_state.candidate.dict()
    missing = next_missing_field(c)
    if not missing:
        return "Thanks! I have your details. Would you like to answer a few technical questions next?"
    prompts = {
        "full_name": "Could you share your full name?",
        "email": "Please provide your email address.",
        "phone": "What is your phone number (with country code if applicable)?",
        "experience": "How many years of professional experience do you have? (e.g., 2 or 2.5)",
        "position": "What role are you targeting? (e.g., Data Scientist, Backend Engineer)",
        "location": "Where are you currently located (city, country)?",
        "tech_stack": "Please list your tech stack (languages, frameworks, databases, tools)."
    }
    return prompts[missing]

# ------------- Chat UI -------------
with right:
    st.markdown("### 💬 Interview Assistant")
    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        css = "assistant" if msg["role"] == "assistant" else "user"
        st.markdown(f"<div class='bubble {css}'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.text_input("Type your message and press Enter")

    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input
        lang = detect_language(user_input)
        mood = rule_sentiment(user_input)

        st.session_state.messages.append({"role": "user", "content": user_input})

        if detect_exit(user_input):
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Thank you for your time! {mood} We'll review your details and get back to you with next steps."
            })
            st.stop()

        # Extract fields
        enrich_candidate_from_text(user_input)

        # Generate response (LLM or deterministic fallback)
        try:
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
            c_json = json.dumps(st.session_state.candidate.dict(), default=str)
            messages = [
                {"role":"system","content": SYSTEM_PROMPT},
                {"role":"user","content": f"The user said: {user_input}\n\nCandidate so far: {c_json}\n\nConversation:\n{history}\n\nReply in language code: {lang}."}
            ]
            reply = chat(system_prompt=SYSTEM_PROMPT, messages=messages, temperature=0.2, max_tokens=400)
        except LLMUnavailable:
            reply = ask_for_next_field()

        # Tech questions (once after we have a stack)
        if st.session_state.candidate.tech_stack and not st.session_state.asked_tech_questions:
            qs = generate_tech_questions(st.session_state.candidate.tech_stack)
            st.session_state.messages.append({"role": "assistant", "content": "Great. Based on your tech stack, please answer these:\n" + "\n".join([f"{i+1}. {q}" for i,q in enumerate(qs)])})
            st.session_state.asked_tech_questions = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": reply})

        st.rerun()
