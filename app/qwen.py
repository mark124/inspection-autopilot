"""Qwen client via Alibaba Cloud Model Studio (DashScope), OpenAI-compatible mode.

Set DASHSCOPE_API_KEY to go live. Without a key the app runs in STUB mode:
deterministic heuristic output with the same JSON shape, clearly labeled in the
UI, so the whole approval workflow is testable offline. Demos use live mode.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


class QwenError(RuntimeError):
    pass


class QwenClient:
    def __init__(self):
        self.api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        self.base_url = os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL)
        self.model = os.environ.get("QWEN_MODEL", DEFAULT_MODEL)
        self._client = None
        if self.api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    @property
    def mode(self) -> str:
        return "live" if self._client else "stub"

    def complete_json(self, system: str, user: str, stub_payload: Optional[dict] = None) -> dict:
        """One JSON-object completion. In stub mode returns stub_payload."""
        if self._client is None:
            if stub_payload is None:
                raise QwenError("stub mode requires a stub_payload")
            return stub_payload

        last_err: Optional[Exception] = None
        for attempt in range(2):
            kwargs = dict(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            try:
                resp = self._client.chat.completions.create(**kwargs)
            except Exception as e:
                # some models reject response_format; the prompts already demand
                # JSON-only replies, so retry without it before giving up
                if "response_format" in str(e):
                    kwargs.pop("response_format")
                    resp = self._client.chat.completions.create(**kwargs)
                else:
                    raise
            text = resp.choices[0].message.content or ""
            try:
                return _extract_json(text)
            except ValueError as e:
                last_err = e
                user = user + "\n\nYour previous reply was not valid JSON. Reply with ONLY a JSON object."
        raise QwenError(f"model returned invalid JSON twice: {last_err}")


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError("no JSON object found")
        obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON is not an object")
    return obj
