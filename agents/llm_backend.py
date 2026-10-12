"""Pluggable text-generation backend.

Ships with zero external dependencies and no API keys: the template
backend is deterministic and is what every dossier line actually uses.
Setting AZURE_FOUNDRY_ENDPOINT + AZURE_FOUNDRY_KEY switches to real model
calls for *phrasing only* — the narrative_generator still supplies the
fixed facts and citations, so a configured model can rewrite the sentence
but never invent a new claim.
"""
import json
import os
import urllib.request
from abc import ABC, abstractmethod


class LLMBackend(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...


class TemplateBackend(LLMBackend):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return user_prompt


class AzureFoundryBackend(LLMBackend):
    def __init__(self, endpoint: str, api_key: str, deployment: str):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version=2024-06-01"
        body = json.dumps({
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 160,
        }).encode()
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json", "api-key": self.api_key},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
        return payload["choices"][0]["message"]["content"]


def get_backend() -> LLMBackend:
    endpoint = os.environ.get("AZURE_FOUNDRY_ENDPOINT")
    api_key = os.environ.get("AZURE_FOUNDRY_KEY")
    deployment = os.environ.get("AZURE_FOUNDRY_DEPLOYMENT", "gpt-4o-mini")
    if endpoint and api_key:
        return AzureFoundryBackend(endpoint, api_key, deployment)
    return TemplateBackend()
