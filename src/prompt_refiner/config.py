from __future__ import annotations

from dataclasses import dataclass

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "phi3:mini"


@dataclass(frozen=True)
class RefinerConfig:
    """
    Central configuration for prompt refinement.

    Notes:
    - Keep defaults conservative so small local models behave well.
    - timeout_s is for the HTTP call to Ollama.
    """
    ollama_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_MODEL
    timeout_s: int = 60
    temperature: float = 0.2
