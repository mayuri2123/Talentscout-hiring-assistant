import os
from typing import List, Dict
from dotenv import load_dotenv
load_dotenv()


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Optional

class LLMUnavailable(Exception):
    pass

def _openai_client():
    try:
        from openai import OpenAI
    except Exception as e:
        raise LLMUnavailable("openai package not installed") from e
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailable("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def chat(system_prompt: str, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500) -> str:
    # This function tries OpenAI; if missing or error, raises LLMUnavailable
    try:
        client = _openai_client()
        msgs = messages if messages and messages[0].get("role") == "system" else ([{"role":"system","content": system_prompt}] + messages)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise LLMUnavailable(str(e))
