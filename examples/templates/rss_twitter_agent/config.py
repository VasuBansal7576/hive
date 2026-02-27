"""Configuration for RSS-to-Twitter Agent."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    model: str = os.getenv("LLM_MODEL", "ollama/llama3.2")
    api_key: str | None = os.getenv("LLM_API_KEY")
    api_base: str | None = os.getenv("LLM_API_BASE")
    max_tokens: int = 4096


@dataclass
class AgentMetadata:
    name: str = "RSS-to-Twitter Agent"
    version: str = "2.0.0"
    description: str = "Fetch RSS, generate tweet threads, request approval, and post via Playwright"


default_config = AgentConfig()
metadata = AgentMetadata()
