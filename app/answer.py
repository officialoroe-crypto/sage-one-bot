"""Turn an internal task/mission result into the plain answer a person should read.

Workers return rich structures (plan, history, events, synthesis). People should see only the answer,
so chat shows this text and the full structure stays on the task record for debugging.
"""
from __future__ import annotations

import ast
import json
from typing import Any

_TEXT_KEYS = ("final", "answer", "response", "text", "output", "summary", "message")


def _as_data(value: Any) -> Any:
    if isinstance(value, str):
        s = value.strip()
        if s[:1] in "{[":
            for loader in (json.loads, ast.literal_eval):
                try:
                    return loader(s)
                except Exception:
                    continue
    return value


def _first_text(data: Any, depth: int = 0) -> str:
    data = _as_data(data)
    if isinstance(data, str):
        return data.strip()
    if depth > 4:
        return ""
    if isinstance(data, dict):
        for key in _TEXT_KEYS:
            if key in data:
                text = _first_text(data[key], depth + 1)
                if text:
                    return text
        if "result" in data:
            return _first_text(data["result"], depth + 1)
    if isinstance(data, list):
        parts = [t for t in (_first_text(item, depth + 1) for item in data) if t]
        return "\n\n".join(parts)
    return ""


def extract_answer(result: Any) -> str:
    """Best plain-text answer for a task result; never a raw data dump if a real answer exists."""
    data = _as_data(result)
    if isinstance(data, dict):
        inner = data.get("result") if isinstance(data.get("result"), dict) and "execution" not in data else None
        if inner is not None:
            data = inner
        synthesis = ((data.get("execution") or {}).get("synthesis") or {}).get("result") if isinstance(data.get("execution"), dict) else None
        synthesis = _as_data(synthesis)
        if isinstance(synthesis, dict):
            parts = []
            for item in synthesis.get("key_results") or []:
                text = _first_text(item.get("result") if isinstance(item, dict) else item)
                if text:
                    parts.append(text)
            if parts:
                return "\n\n".join(parts)
            summary = _first_text(synthesis.get("summary"))
            if summary:
                return summary
    text = _first_text(data)
    if text:
        return text
    return "Done."
