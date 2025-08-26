import os
from typing import List, Dict

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

class LLMUnavailable(Exception):
    pass

def _openai_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailable("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)

def chat(system_prompt: str, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 500) -> str:
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages if messages and messages[0].get("role") == "system" else [{"role":"system","content": system_prompt}] + messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise LLMUnavailable(str(e))
