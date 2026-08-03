from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class LunaProvider(ModelProvider):
    """OpenAI-compatible Luna adapter configured entirely outside source code."""

    def __init__(self, config: LunaConfig):
        self.config = config

    @classmethod
    def from_env(cls) -> "LunaProvider":
        base_url = os.environ.get("LUNA_BASE_URL")
        model = os.environ.get("LUNA_MODEL")
        if not base_url or not model:
            raise RuntimeError("Set LUNA_BASE_URL and LUNA_MODEL before using LunaProvider")
        return cls(
            LunaConfig(
                base_url=base_url,
                model=model,
                api_key=os.environ.get("LUNA_API_KEY"),
                timeout_seconds=int(os.environ.get("LUNA_TIMEOUT_SECONDS", "90")),
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
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
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
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Luna request failed with HTTP {error.code}: {details[:500]}") from error
        except URLError as error:
            raise RuntimeError(f"Cannot reach Luna endpoint: {error.reason}") from error
        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Luna returned an unexpected response shape") from error
        return _parse_json_object(content)


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
