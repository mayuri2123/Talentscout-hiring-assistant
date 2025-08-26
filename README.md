# TalentScout — AI/ML Intern Assignment Solution

A Streamlit-based **Hiring Assistant chatbot** that collects candidate information and asks **tech‑stack–tailored** questions. Built to meet the assignment requirements end-to-end, with **LLM support (optional)** and **deterministic fallback**.

## Features

- Modern two‑column UI (candidate summary + chat) with styled chat bubbles.
- Greeting + purpose, exit keywords handling.
- Collects: Full name, Email, Phone, Experience, Desired Position, Location, Tech Stack.
- Generates **3–5 technical questions** based on the declared tech stack (LLM or fallback bank).
- Context-aware responses; fallback guidance when input is unclear.
- Optional sentiment cue 🙂/😐/😕 (rule-based).
- Multilingual friendliness (simple detect; mirror language when LLM available).
- Optional **PII encryption** (email/phone) on save using `cryptography.Fernet`.
- Local deployment; cloud-ready.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -r requirements.txt
streamlit run app.py
```

### Optional: OpenAI (LLM) Integration

Set env vars before running:
```bash
export OPENAI_API_KEY=YOUR_KEY
export OPENAI_MODEL=gpt-4o-mini
```

> If `OPENAI_API_KEY` is not set or `openai` is not installed, the app falls back to deterministic prompts and the built-in question bank.

### Optional: Encrypt PII on Save

```bash
python - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY

export ENABLE_ENCRYPTION=true
export ENCRYPTION_KEY=that_generated_key
```

## Repository Structure

```
talentscout/
├── app.py
├── llm.py
├── prompts.py
├── questions_bank.py
├── utils.py
├── requirements.txt
└── README.md
```

## Prompt Design

- **System Prompt** (`prompts.py: SYSTEM_PROMPT`) sets role, scope, guardrails, and data collection order.
- **Tech Q Prompt** (`TECH_QA_PROMPT`) asks for short, practical, balanced questions across listed technologies.

## Data Privacy

- No data is sent anywhere by default (unless you provide an OpenAI API key).
- Saved snapshots are written to `data/` only when the user clicks **Save Profile Snapshot**.
- Optional encryption for email/phone via Fernet. Remove keys to disable.
- For real deployments, add: cookie banners, ToS/Privacy links, and a retention policy.

## Challenges & Solutions

- **No network / LLM unavailability**: Implemented deterministic fallback and local question bank.
- **Sentiment without downloads**: Used a lightweight rule-based sentiment cue.
- **Robust parsing**: Regex-based extraction for email/phone/experience; simple heuristics for name/position/location/stack.
- **Context**: Recent conversation window + candidate JSON provided to LLM (when available).

## Cloud Deployment (Bonus)

- **Streamlit Community Cloud**: Push to GitHub, then deploy: https://share.streamlit.io/
- **AWS EC2**: Ubuntu VM, install Python + `pip`, `tmux`, run `streamlit run --server.port 80 --server.address 0.0.0.0` behind a security group.
- **GCP Cloud Run**: Containerize with a simple Dockerfile and deploy.

## License

For assignment/demo use.👉 [Watch the Loom Demo](https://www.loom.com/share/92bf9842815947c0b9c4476354027462?sid=a2048262-26b2-4d7e-b0f7-c2aa9b4dea68)  

