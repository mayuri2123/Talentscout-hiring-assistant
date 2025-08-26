import os
import json
import base64
import io
from datetime import datetime
from typing import Optional

import streamlit as st
from pydantic import BaseModel, EmailStr

from prompts import SYSTEM_PROMPT
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

# ----------------------------------
# Candidate Model
# ----------------------------------
class Candidate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    experience: Optional[float] = None
    position: Optional[str] = None
    location: Optional[str] = None
    tech_stack: Optional[str] = None

    def is_complete(self) -> bool:
        return all([
            self.full_name, self.email, self.phone,
            self.experience is not None, self.position,
            self.location, self.tech_stack
        ])

# ----------------------------------
# Session State
# ----------------------------------
if "candidate" not in st.session_state:
    st.session_state.candidate = Candidate()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "asked_tech_questions" not in st.session_state:
    st.session_state.asked_tech_questions = False
if "last_input" not in st.session_state:
    st.session_state.last_input = None

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
/* Hero */
.hero {
  background:#0b1f3a;
  padding:60px 20px;
  text-align:center;
  border-radius:12px;
  margin-bottom:18px;
  color:white;
}
.hero h1{ margin:0 0 6px 0; }
.hero p{ color:#d6dce5; font-size:18px; margin: 8px 0 22px 0; }
.hero .cta {
  background:#e74c3c;
  color:white; border:none; padding:12px 24px;
  border-radius:25px; font-weight:700; font-size:16px; cursor:pointer;
}

/* Candidate card */
.card {
  background: #f7f9fb;
  border: 1px solid #e5e8eb;
  border-radius: 12px;
  padding: 14px 16px;
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
# 🚀 Exit Page Helpers
# ----------------------------------
def make_json_download_button(data: dict, filename: str = "candidate_profile.json", label: str = "⬇️ Download your profile JSON"):
    buf = io.BytesIO(json.dumps(data, indent=2).encode("utf-8"))
    b64 = base64.b64encode(buf.getvalue()).decode()
    href = f'<a download="{filename}" href="data:file/json;base64,{b64}" style="text-decoration:none">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

def show_exit_screen():
    st.markdown("""
    <div style="text-align:center; padding:32px">
      <h2>✅ Thanks for your time!</h2>
      <p>We’ve captured your details. Here’s what happens next:</p>
      <ol style="text-align:left; display:inline-block;">
        <li>Recruiter reviews your profile</li>
        <li>We schedule an interview</li>
        <li>Technical + HR interview rounds</li>
        <li>Offer decision</li>
      </ol>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Your Profile Snapshot")
    st.code(json.dumps(st.session_state.candidate.dict(), indent=2), language="json")
    make_json_download_button(st.session_state.candidate.dict())

    redirect = os.getenv("EXIT_REDIRECT_URL")
    colA, colB = st.columns([1, 1])
    with colA:
        if redirect and st.button("🏁 Go to Next Step / Portal"):
            st.markdown(f"<meta http-equiv='refresh' content='0; url={redirect}'>", unsafe_allow_html=True)
    with colB:
        if st.button("🔄 Start Over"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    st.stop()

# ----------------------------------
# Hero (Taira-like)
# ----------------------------------
st.markdown(f"""
<div class="hero">
  <h1>🧭 TalentScout — Virtual Hiring Assistant</h1>
  <p>AI-powered recruitment: collect candidate details and assess skills with tailored technical questions.</p>
  <a href="#chat"><button class="cta">🚀 Start Interview</button></a>
</div>
""", unsafe_allow_html=True)

# ----------------------------------
# Sidebar
# ----------------------------------
with st.sidebar:
    st.markdown("## 💡 How to use")
    st.markdown("""
- Answer the questions the assistant asks (you can provide multiple details at once).
- Say **exit** to finish anytime (you'll see a summary + next steps).
- When complete, you can **save** your profile to JSON.
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
            st.success(f"Profile saved to `{path}`")

# ----------------------------------
# Finish & Exit button (always visible)
# ----------------------------------
top_left, top_right = st.columns([3,1])
with top_right:
    if st.button("Finish & Exit", use_container_width=True):
        show_exit_screen()

# ----------------------------------
# Progress bar (profile completeness)
# ----------------------------------
def _completion_ratio(c: Candidate) -> float:
    vals = c.dict()
    total = len(vals)
    filled = sum(1 for k, v in vals.items() if (v is not None and v != ""))
    return filled / total if total else 0.0

st.progress(_completion_ratio(st.session_state.candidate))

# ----------------------------------
# Greeting (first message)
# ----------------------------------
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "👋 Hi! I’m TalentScout, your virtual recruiter. Let’s start with the basics — what’s your **full name**?"
    })

# ----------------------------------
# Helper: next recruiter-style question
# ----------------------------------
def next_recruiter_question(cand: Candidate) -> Optional[str]:
    if not cand.full_name:
        return "Great to meet you! What’s your **full name**?"
    if not cand.email:
        return "Thanks! What’s the best **email address** to contact you?"
    if not cand.phone:
        return "Perfect. Could you provide your **phone number** (with country code if possible)?"
    if cand.experience is None:
        return "Nice. How many **years of professional experience** do you have?"
    if not cand.position:
        return "Got it. What **position or role** are you applying for?"
    if not cand.location:
        return "Thanks. Where are you currently **located** (city/country)?"
    if not cand.tech_stack:
        return "Awesome. Please list your **tech stack** — languages, frameworks, databases, and tools."
    return None

# ----------------------------------
# Layout
# ----------------------------------
left, right = st.columns([1, 2])

# Candidate Summary (left)
with left:
    st.markdown("### 📝 Candidate Summary")
    c = st.session_state.candidate
    st.markdown(f"""
    <div class='card'>
      <div>👤 <b>Full Name:</b> {safe_display(c.full_name)}</div>
      <div>📧 <b>Email:</b> {safe_display(c.email)}</div>
      <div>📱 <b>Phone:</b> {safe_display(c.phone)}</div>
      <div>💼 <b>Experience:</b> {safe_display(f"{c.experience} years" if c.experience is not None else None)}</div>
      <div>🎯 <b>Position:</b> {safe_display(c.position)}</div>
      <div>📍 <b>Location:</b> {safe_display(c.location)}</div>
      <div>🛠️ <b>Tech Stack:</b> {safe_display(c.tech_stack)}</div>
    </div>
    """, unsafe_allow_html=True)

# Chat (right)
with right:
    st.markdown("<div id='chat'></div>", unsafe_allow_html=True)
    st.markdown("### 💬 Interview Assistant")

    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        role = msg["role"]
        css_class = "assistant" if role == "assistant" else "user"
        avatar = "🤖" if role == "assistant" else "👤"
        st.markdown(f"<div class='bubble {css_class}'>{avatar} {msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Friendly input label
    user_input = st.text_input("✍️ Your answer:", key="chat_input")

    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Exit flow
        if detect_exit(user_input):
            show_exit_screen()

        # Process multiple inputs in one go (fast + user-friendly)
        cand = st.session_state.candidate
        for piece in [p.strip() for p in user_input.replace("\n", ",").split(",") if p.strip()]:
            email = extract_email(piece)
            phone = extract_phone(piece)
            exp = extract_experience(piece)

            if email and not cand.email:
                cand.email = email
                continue
            if phone and not cand.phone:
                cand.phone = phone
                continue
            if exp is not None and cand.experience is None:
                cand.experience = exp
                continue

            # Lightweight heuristics for other fields
            lower = piece.lower()
            if any(k in lower for k in ["engineer", "developer", "scientist", "analyst", "intern", "manager"]) and not cand.position:
                cand.position = piece
                continue
            if any(k in lower for k in ["python","java","sql","django","flask","react","node","pytorch","tensorflow","pandas","numpy","ml","scikit","mongodb","mysql","postgres"]) and not cand.tech_stack:
                cand.tech_stack = piece
                continue
            if any(k in lower for k in ["nagpur","pune","mumbai","delhi","bangalore","hyderabad","remote","india","usa","uk","london","new york"]) and not cand.location:
                cand.location = piece
                continue
            # Assume full name if it looks like two+ words and name not set
            if " " in piece and not cand.full_name and not any(ch.isdigit() for ch in piece):
                cand.full_name = piece.title()

        # Decide next message
        nxt = next_recruiter_question(cand)
        if nxt:
            # Keep it snappy without always calling LLM
            st.session_state.messages.append({"role": "assistant", "content": nxt})
        else:
            # Candidate profile is complete
            if not st.session_state.asked_tech_questions:
                # Ask tailored questions (fallback)
                qs = generate_fallback_questions(cand.tech_stack, max_questions=5)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Great! Based on your tech stack, here are some questions:\n" +
                               "\n".join([f"{i+1}. {q}" for i, q in enumerate(qs)])
                })
                st.session_state.asked_tech_questions = True
            else:
                # Optionally ask LLM for a follow-up/context message (short history for speed)
                try:
                    system = SYSTEM_PROMPT
                    messages = [{"role":"system","content": system}] + st.session_state.messages[-5:]
                    reply = chat(system_prompt=system, messages=messages, temperature=0.2, max_tokens=300)
                except LLMUnavailable:
                    reply = "Thanks! Please answer the questions above. Type **exit** whenever you’re done."
                st.session_state.messages.append({"role": "assistant", "content": reply})

        # Refresh UI
        st.rerun()
