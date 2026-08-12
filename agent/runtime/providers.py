from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent.core import get_contract, validate_document


class ModelProvider(ABC):
    """Small provider boundary so model choice does not leak into the pipeline."""

    @abstractmethod
    def generate_json(
        self,
        *,
        task: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class LunaConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: int = 90
    api_mode: str = "auto"


class LunaProvider(ModelProvider):
    """OpenAI-compatible Luna adapter configured entirely outside source code."""

    def __init__(self, config: LunaConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "LunaProvider":
        _load_local_env()
        base_url = os.environ.get("LUNA_BASE_URL", "https://api.cutaihub.com/v1")
        model = os.environ.get("LUNA_MODEL", "gpt-5.6-luna")
        return cls(
            LunaConfig(
                base_url=base_url,
                model=model,
                api_key=os.environ.get("LUNA_API_KEY"),
                timeout_seconds=int(os.environ.get("LUNA_TIMEOUT_SECONDS", "90")),
                api_mode=os.environ.get("LUNA_API_MODE", "auto").lower(),
            )
        )

    def generate_json(
        self,
        *,
        task: str,
        payload: dict[str, Any],
        schema: dict[str, Any],
        feedback: list[str] | None = None,
    ) -> dict[str, Any]:
        if not self.config.api_key:
            raise RuntimeError(
                "LUNA_API_KEY is not configured. Put it in the local .env file or set it as an environment variable."
            )
        system = (
            "You are the semantic planning model inside a PPT Agent. "
            "Return exactly one JSON object and no markdown. Never invent data or sources. "
            "Use Chinese when the input language is zh-CN."
        )
        user = {
            "task": task,
            "input": payload,
            "output_schema": schema,
            "validation_feedback": feedback or [],
        }
        if self.config.api_mode not in {"auto", "chat", "responses"}:
            raise RuntimeError("LUNA_API_MODE must be auto, chat, or responses")
        if self.config.api_mode == "chat":
            return self._generate_chat(system, user)
        if self.config.api_mode == "responses":
            return self._generate_responses(system, user, schema)
        try:
            return self._generate_responses(system, user, schema)
        except LunaHTTPError as error:
            if error.status_code not in {404, 405}:
                raise
            return self._generate_chat(system, user)

    def _generate_responses(
        self, system: str, user: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        body = {
            "model": self.config.model,
            "instructions": system,
            "input": json.dumps(user, ensure_ascii=False),
            "text": {"format": {"type": "json_object"}},
        }
        result = self._post("/responses", body)
        content = result.get("output_text") or _extract_response_text(result.get("output"))
        if not content:
            raise RuntimeError("Luna Responses API returned no output text")
        return _parse_json_object(content)

    def _generate_chat(self, system: str, user: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        result = self._post("/chat/completions", body)
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Luna returned an unexpected chat response shape") from error
        return _parse_json_object(content)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.config.base_url.rstrip('/')}{path}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PPT-Agent/0.2",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        request = Request(
            endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise LunaHTTPError(error.code, details[:500]) from error
        except URLError as error:
            raise RuntimeError(f"Cannot reach Luna endpoint: {error.reason}") from error


class ScriptedProvider(ModelProvider):
    """Deterministic provider for tests and offline demos."""

    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = list(responses)
        self.calls: list[str] = []

    def generate_json(self, *, task: str, payload: dict[str, Any], schema: dict[str, Any], feedback: list[str] | None = None) -> dict[str, Any]:
        self.calls.append(task)
        if not self.responses:
            raise RuntimeError(f"No scripted response remains for task: {task}")
        return self.responses.pop(0)


class ContractGenerator:
    def __init__(self, provider: ModelProvider, max_attempts: int = 3):
        self.provider = provider
        self.max_attempts = max_attempts

    def generate(
        self,
        *,
        task: str,
        payload: dict[str, Any],
        contract_name: str,
        contract_version: str,
    ) -> dict[str, Any]:
        contract = get_contract(contract_name, contract_version)
        schema = json.loads(contract.path.read_text(encoding="utf-8"))
        feedback: list[str] = []
        for _ in range(self.max_attempts):
            document = self.provider.generate_json(
                task=task,
                payload=payload,
                schema=schema,
                feedback=feedback,
            )
            feedback = validate_document(document, contract_name, contract_version)
            if not feedback:
                return document
        details = "\n".join(f"- {item}" for item in feedback[:20])
        raise ValueError(f"Model output did not satisfy {contract_name}@{contract_version}:\n{details}")


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
        if text.startswith("json"):
            text = text[4:].lstrip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("Expected the model to return a JSON object")
    return parsed


class LunaHTTPError(RuntimeError):
    def __init__(self, status_code: int, details: str):
        super().__init__(f"Luna request failed with HTTP {status_code}: {details}")
        self.status_code = status_code


def _extract_response_text(output: Any) -> str:
    if not isinstance(output, list):
        return ""
    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _load_local_env() -> None:
    """Load simple KEY=VALUE entries from the project-local .env, without overriding the shell."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (key not in os.environ or not os.environ[key]):
            os.environ[key] = value
