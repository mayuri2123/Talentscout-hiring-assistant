import os
import json
import base64
import io
from datetime import datetime
from typing import Optional, List

import streamlit as st
from pydantic import BaseModel, EmailStr

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

    def is_complete(self):
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
      <p>We’ve captured your details. Our team will review and reach out with the next steps.</p>
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
# Header
# ----------------------------------
st.markdown("<div class='main-header'><h1>🧭 TalentScout — AI Hiring Assistant</h1><p class='tagline'>Collect candidate info and assess skills with tailored technical questions</p></div>", unsafe_allow_html=True)

# 🚀 Finish & Exit button always available
top_left, top_right = st.columns([3,1])
with top_right:
    if st.button("Finish & Exit", use_container_width=True):
        show_exit_screen()

left, right = st.columns([1, 2])

# ----------------------------------
# Candidate summary
# ----------------------------------
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

# ----------------------------------
# Greeting
# ----------------------------------
if not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I’m TalentScout, your AI hiring assistant. I’ll collect your details and ask you technical questions based on your tech stack. You can type 'exit' anytime to finish."})

# ----------------------------------
# Right column (chat)
# ----------------------------------
with right:
    st.markdown("### 💬 Interview Assistant")
    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        css_class = "assistant" if msg["role"] == "assistant" else "user"
        st.markdown(f"<div class='bubble {css_class}'>{msg['content']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    user_input = st.text_input("Type your message and press Enter")

    if user_input and user_input != st.session_state.last_input:
        st.session_state.last_input = user_input
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 🚀 Exit flow
        if detect_exit(user_input):
            show_exit_screen()

        # 🚀 Process multiple inputs in one go
        # Split by comma or newline for batch input
        for piece in [p.strip() for p in user_input.replace("\n", ",").split(",") if p.strip()]:
            email = extract_email(piece)
            phone = extract_phone(piece)
            exp = extract_experience(piece)

            if email:
                c.email = email
            elif phone:
                c.phone = phone
            elif exp is not None:
                c.experience = exp
            elif any(k in piece.lower() for k in ["engineer","developer","scientist","analyst","intern","manager"]):
                c.position = c.position or piece
            elif any(k in piece.lower() for k in ["python","java","sql","django","flask","react","node","pytorch","tensorflow","pandas","numpy","ml"]):
                c.tech_stack = c.tech_stack or piece
            elif any(k in piece.lower() for k in ["nagpur","pune","mumbai","delhi","bangalore","hyderabad","remote","india","usa","uk"]):
                c.location = c.location or piece
            elif " " in piece and not c.full_name:
                c.full_name = piece.title()

        # 🚀 Efficiently decide assistant reply
        try:
            system = SYSTEM_PROMPT
            messages = [{"role":"system","content": system}] + st.session_state.messages[-5:]
            reply = chat(system_prompt=system, messages=messages, temperature=0.2, max_tokens=300)
        except LLMUnavailable:
            reply = "Got it ✅ Please continue..."

        # 🚀 Ask tech questions only once
        if c.tech_stack and not st.session_state.asked_tech_questions:
            qs = generate_fallback_questions(c.tech_stack, max_questions=5)
            st.session_state.messages.append({"role": "assistant", "content": "Great! Based on your tech stack, here are some questions:\n" + "\n".join([f"{i+1}. {q}" for i,q in enumerate(qs)])})
            st.session_state.asked_tech_questions = True
        else:
            st.session_state.messages.append({"role": "assistant", "content": reply})

        st.rerun()
