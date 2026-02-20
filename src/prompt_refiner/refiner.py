from __future__ import annotations

from typing import Any, Dict

from .config import RefinerConfig
from .ollama_client import OllamaClient
from .prompts.refinement_prompt import SYSTEM_INSTRUCTIONS, build_user_message


def refine_prompt(raw_prompt: str, cfg: RefinerConfig) -> Dict[str, Any]:
    client = OllamaClient(cfg.ollama_url, timeout_s=cfg.timeout_s)

    assistant_text = client.chat(
        model=cfg.model,
        system=SYSTEM_INSTRUCTIONS,
        user=build_user_message(raw_prompt),
        temperature=cfg.temperature,
    )

    return {
        "structured_prompt": (assistant_text or "").strip(),
        "meta": {
            "model": cfg.model,
            "ollama_url": cfg.ollama_url,
        },
    }
