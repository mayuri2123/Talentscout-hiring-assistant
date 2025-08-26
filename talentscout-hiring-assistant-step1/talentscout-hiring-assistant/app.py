import os
import json
from datetime import datetime
from typing import Optional, List

import streamlit as st
from pydantic import BaseModel, EmailStr
from langdetect import detect
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from prompts import SYSTEM_PROMPT, TECH_QA_PROMPT
from llm import chat, LLMUnavailable
from utils import (
    extract_email, extract_phone, extract_experience, next_missing_field,
    detect_exit, secure_store, safe_display
)
from questions_bank import generate_fallback_questions

# ----------------------------------
# Setup
# ----------------------------------
st.set_page_config(page_title="TalentScout - AI Hiring Assistant", page_icon="🧭", layout="wide")

# Ensure nltk data for VADER
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')
SIA = SentimentIntensityAnalyzer()

# ----------------------------------
# Models
# ----------------------------------
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

# ----------------------------------
# State
# ----------------------------------
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

# ----------------------------------
# Styles
# ----------------------------------
st.markdown("""
<style>
/* Sidebar */
[data-testid="stSidebar"] {
  background: #0b1f3a;
  color: #fff;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] li {
  color: #fff !important;
}
/* Header */
.main-header {
  background: linear-gradient(120deg, #2E86C1, #1B4F72);
  padding: 24px 20px;
  border-radius: 14px;
  text-align: center;
  color: white;
  margin-bottom: 16px;
}
.tagline {
  font-size: 15px;
  color: #eaf2f8;
  margin-top: -6px;
}
/* Candidate card */
.card {
  background: #f7f9fb;
  border: 1px solid #e5e8eb;
  border-radius: 12px;
  padding: 14px 16px;
}
.key {
  color: #2c3e50;
  font-weight: 600;
}
/* Chat */
.chat-wrap {
  height: 460px;
  overflow-y: auto;
  border: 1px solid #e5e8eb;
  border-radius: 12px;
  background: #fbfcfd;
  padding: 8px;
}
.bubble.assistant {
  background: #d6eaf8;
  color: #0b3750;
  border-radius: 12px;
  padding: 10px 12px;
  margin: 6px;
  max-width: 85%;
}
.bubble.user {
  background: #d1f2eb;
  color: #0b5044;
  border-radius: 12px;
  padding: 10px 12px;
  margin: 6px;
  margin-left: auto;
  max-width: 85%;
}
/* Buttons */
.stButton>button {
  background: #2E86C1;
  color: white;
  border-radius: 10px;
  padding: 8px 14px;
  border: 0;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------
# Sidebar
# ----------------------------------
with st.sidebar:
    st.markdown("## 💡 How to use")
    st.markdown("""
- Type your responses in the chat box.
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

# ----------------------------------
# Header & Layout
# ----------------------------------
st.markdown("<div class='main-header'><h1>🧭 TalentScout — AI Hiring Assistant</h1><p class='tagline'>Collect candidate info and assess skills with tailored technical questions</p></div>", unsafe_allow_html=True)
left, right = st.columns([1, 2])

# ----------------------------------
# Candidate summary
# ----------------------------------
with left:
    st.markdown("### 📝 Candidate Summary")
    c = st.session_state.candidate
    st.markdown(f"""
    <div class='card'>
      <div><span class='key'>👤 Full Name:</span> {safe_display(c.full_name)}</div>
      <div><span class='key'>📧 Email:</span> {safe_display(c.email)}</div>
      <div><span class='key'>📱 Phone:</span> {safe_display(c.phone)}</div>
      <div><span class='key'>💼 Experience:</span> {safe_display(f"{c.experience} years" if c.experience is not None else None)}</div>
      <div><span class='key'>🎯 Position:</span> {safe_display(c.position)}</div>
      <div><span class='key'>📍 Location:</span> {safe_display(c.location)}</div>
      <div><span class='key'>🛠️ Tech Stack:</span> {safe_display(c.tech_stack)}</div>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------
# Greeting (once)
# ----------------------------------
def ensure_greeting():
    if not st.session_state.messages:
        greeting = ("Hello! I’m TalentScout, your AI hiring assistant. "
                    "I’ll collect your basic details (name, contact, experience, position, location, tech stack) "
                    "and then ask a few tailored technical questions. You can type 'exit' anytime to end.")
        st.session_state.messages.append({"role": "assistant", "content": greeting})
ensure_greeting()

# ----------------------------------
# Core helpers
# ----------------------------------
def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "en" if lang not in ("hi","es","fr","de","it","pt","bn","mr","ta","te","gu","pa","ur","zh-cn","zh-tw","ja","ko","ru") else lang
    except Exception:
        return "en"

def enrich_candidate_from_text(text: str):
    c = st.session_state.candidate
    email = extract_email(text)
    phone = extract_phone(text)
    exp = extract_experience(text)

    # naive extraction by heuristics
    lower = text.lower()

    if email:
        c.email = email
    if phone:
        c.phone = phone
    if exp is not None:
        c.experience = exp

    # position guess
    if any(k in lower for k in ["engineer","developer","scientist","analyst","manager","intern"]):
        c.position = (c.position or text)

    # tech stack capture: after "tech stack:" or comma-separated list with known keywords
    if "tech stack" in lower or any(k in lower for k in ["python","java","sql","django","flask","react","node","pytorch","tensorflow","pandas","numpy","ml","machine learning"]):
        # naive: assign full text; better UX would parse after colon
        c.tech_stack = (c.tech_stack or text)

    # location guess
    if "location" in lower or any(k in lower for k in ["nagpur","pune","mumbai","delhi","bangalore","bengaluru","hyderabad","remote","india","usa","uk","europe"]):
        c.location = (c.location or text)

    # full name guess: if looks like two words and not already set
    if " " in text.strip() and not c.full_name and not email and not phone:
        c.full_name = text.strip().title()

def generate_tech_questions(tech_stack: str) -> List[str]:
    # try LLM first
    try:
        prompt = TECH_QA_PROMPT.format(tech_stack=tech_stack)
        msg = [{"role":"system","content": "You generate concise interview questions."},
               {"role":"user","content": prompt}]
        out = chat(system_prompt="", messages=msg, temperature=0.2, max_tokens=400)
        # Parse numbered list
        lines = [ln.strip(" -") for ln in out.strip().splitlines() if ln.strip()]
        questions = []
        for ln in lines:
            # remove leading numbers like "1. " or "1) "
            q = ln
            q = q.split(") ",1)[-1] if ") " in q and q[0].isdigit() else q
            q = q.split(". ",1)[-1] if ". " in q and q[0].isdigit() else q
            questions.append(q.strip())
        # fallback if weird
        if not questions:
            raise ValueError("No questions parsed")
        return questions[:5]
    except Exception:
        return generate_fallback_questions(tech_stack, max_questions=5)

def sentiment_tag(text: str) -> str:
    try:
        score = SIA.polarity_scores(text)["compound"]
        if score >= 0.5:
            return "🙂"
        elif score <= -0.5:
            return "😕"
        else:
            return "😐"
    except Exception:
        return ""

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
        "tech_stack": "Please list your tech stack (languages, frameworks, databases, tools).",
    }
    return prompts[missing]

# ----------------------------------
# Right column (chat)
# ----------------------------------
with right:
    st.markdown("### 💬 Interview Assistant")
    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        css_class = "assistant" if role == "assistant" else "user"
        st.markdown(f"<div class='bubble {css_class}'>{content}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.text_input("Type your message and press Enter")

    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input

        # Language detect & sentiment
        st.session_state.language = detect_language(user_input)
        mood = sentiment_tag(user_input)

        st.session_state.messages.append({"role": "user", "content": user_input})

        if detect_exit(user_input):
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Thank you for your time! {mood} We'll review your details and get back to you with next steps."
            })
            st.stop()

        # Heuristic extraction
        enrich_candidate_from_text(user_input)

        # Decide response: use LLM to keep context if available, else deterministic
        try:
            # Build conversation for LLM
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
            c_json = json.dumps(st.session_state.candidate.dict(), default=str)
            system = SYSTEM_PROMPT
            messages = [
                {"role":"system","content": system},
                {"role":"user","content": f"The user said: {user_input}\n\nCandidate so far: {c_json}\n\nConversation:\n{history}\n\nReply in language code: {st.session_state.language}."}
            ]
            reply = chat(system_prompt=system, messages=messages, temperature=0.2, max_tokens=400)
        except LLMUnavailable:
            # Deterministic fallback: ask for next field or proceed to questions
            reply = ask_for_next_field()

        # Tech questions trigger (once)
        if st.session_state.candidate.tech_stack and not st.session_state.asked_tech_questions:
            qs = generate_tech_questions(st.session_state.candidate.tech_stack)
            st.session_state.messages.append({"role": "assistant", "content": f"Great. Based on your tech stack, please answer these:\n" + "\n".join([f"{i+1}. {q}" for i,q in enumerate(qs)])})
            st.session_state.asked_tech_questions = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": reply})

        st.rerun()
