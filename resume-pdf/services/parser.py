import json
import os
import yaml

import instructor
from openai import OpenAI
from pydantic import ValidationError

from models.resume import ResumeData


def load_content_from_text(raw: str, filename: str = ""):
    """
    Tries to turn raw text into a dict based on JSON or YAML structure.
    Returns None if it's unstructured plain text.
    """
    low = filename.lower()

    if low.endswith((".yaml", ".yml")):
        try:
            parsed = yaml.safe_load(raw)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def load_content(path: str):
    """Utility to read file from disk path."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return load_content_from_text(raw, path)


def parse_text(raw: str) -> ResumeData:
    """
    Sends raw text to Groq LLM via instructor to extract ResumeData.
    instructor automatically enforces the schema and handles retries.
    """
    client = instructor.from_openai(
        OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY", ""),
        ),
        mode=instructor.Mode.MD_JSON,
    )
    llm_model = os.environ.get("PARSE_LLM_MODEL", "groq/compound-mini")

    return client.chat.completions.create(
        model=llm_model,
        response_model=ResumeData,
        max_tokens=3000,
        max_retries=3,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract resume information from the user's text and "
                    "structure it according to the required schema. If a "
                    "field isn't present in the input, omit it or use a "
                    "sensible empty value rather than inventing content."
                ),
            },
            {"role": "user", "content": raw},
        ],
    )


def parse_and_validate(raw: str, filename: str = "") -> ResumeData:
    """
    Unified entry point:
    1. Try structural JSON/YAML parse first.
    2. If valid ResumeData dict, return ResumeData(**parsed).
    3. If unstructured text or malformed JSON, pass to LLM parser (parse_text).
    """
    parsed = load_content_from_text(raw, filename)

    if parsed is not None:
        try:
            return ResumeData(**parsed)
        except ValidationError:
            pass  # Fallback to LLM extraction

    return parse_text(raw)
