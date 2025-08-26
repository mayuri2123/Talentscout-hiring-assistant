
# TalentScout – Hiring Assistant (Streamlit)

A privacy-aware, LLM-powered chatbot that screens tech candidates by collecting essential details and asking tailored technical questions based on the candidate's declared tech stack.

## ✨ Features (MVP in this step)
- Streamlit chat UI with session state
- Guided info collection (7 fields)
- Exit keywords to end the chat
- LLM integration scaffold (OpenAI) with rule-based fallback
- Local JSON snapshot save (for demo only)

> This repository is prepared as a step-by-step build. In **Step 1**, you get a runnable skeleton. We'll expand prompts, validation, question generation, and privacy next.

## 🚀 Quickstart

### 1) Clone & Install
```bash
git clone <your-repo-url> talentscout-hiring-assistant
cd talentscout-hiring-assistant
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure LLM (optional for now)
Create `.env` with:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

> If you skip this, the app still runs with a simple rule-based fallback.

### 3) Run
```bash
streamlit run app.py
```

## 🧱 Structure
```
talentscout-hiring-assistant/
├── app.py
├── prompts.py
├── requirements.txt
├── README.md
├── .gitignore
└── data/
```

## 🔐 Privacy & Data Handling
- Demo-only local storage in `data/`
- Do **not** input highly sensitive personal data
- We will add hashing/encryption and GDPR guidance in later steps

## 📜 License
MIT
