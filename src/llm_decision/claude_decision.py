"""Decisión real vía la API de Claude -- reemplaza al mock (mock_decision.py)
una vez que paper trading está listo para conectarse de verdad. La respuesta
nunca se usa "cruda": siempre pasa por decision_schema.validate_decision()."""

import json

import anthropic
from dotenv import load_dotenv

from src.llm_decision.decision_schema import validate_decision
from src.llm_decision.prompt_template import SYSTEM_PROMPT

load_dotenv()

MODEL = "claude-sonnet-5"

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def claude_decision(market_summary: dict) -> dict:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        output_config={"effort": "low"},  # decisión estructurada y acotada, no necesita razonamiento profundo
        messages=[{"role": "user", "content": json.dumps(market_summary, ensure_ascii=False)}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "")

    try:
        raw = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raw = {"action": "invalid", "reasoning": f"respuesta no parseable: {text[:200]}"}

    return validate_decision(raw)
