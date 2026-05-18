from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMClientError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    content: str


class OpenAIChatClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        base_url: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: int = 45,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "OpenAIChatClient | None":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        model = os.getenv("PREFLIGHT_LLM_MODEL", "gpt-4.1-mini")
        base_url = os.getenv("PREFLIGHT_OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        timeout_seconds = int(os.getenv("PREFLIGHT_LLM_TIMEOUT_SECONDS", "45"))
        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        request = Request(
            url=self.base_url,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8"),
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI HTTP error {exc.code}: {detail}")
        except URLError as exc:
            raise LLMClientError(f"OpenAI request failed: {exc}")

        try:
            content = raw_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError(f"Unexpected OpenAI response format: {raw_payload}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMClientError("OpenAI returned empty content")

        return LLMResponse(content=content)
