from __future__ import annotations

import argparse
import sys

from .config import RefinerConfig, DEFAULT_MODEL, DEFAULT_OLLAMA_URL
from .errors import OllamaConnectionError, OllamaResponseError
from .refiner import refine_prompt


def _print_user_error(e: Exception) -> None:
    print(f"Error: {e}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prompt-refiner",
        description="Refine a raw prompt into a detailed structured prompt using local Ollama.",
    )
    p.add_argument("prompt", nargs="?", help="Raw prompt text. If omitted, read from stdin.")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name (default: {DEFAULT_MODEL})")
    p.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL, help=f"Ollama base URL (default: {DEFAULT_OLLAMA_URL})")
    p.add_argument("--timeout", type=int, default=60, help="HTTP timeout seconds (default: 60)")
    p.add_argument("--list-models", action="store_true", help="List installed Ollama models and exit.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = RefinerConfig(
        ollama_url=args.ollama_url,
        model=args.model,
        timeout_s=args.timeout,
    )

    # IMPORTANT: exit early BEFORE reading stdin
    if args.list_models:
        from .ollama_client import OllamaClient

        c = OllamaClient(cfg.ollama_url, timeout_s=cfg.timeout_s)
        try:
            models = c.list_models()
        except (OllamaConnectionError, OllamaResponseError) as e:
            _print_user_error(e)
            return 2

        if not models:
            print("No models found. Try: ollama pull phi3:mini")
            return 0

        for m in models:
            print(m)
        return 0

    raw = args.prompt
    if raw is None:
        if sys.stdin.isatty():
            parser.print_help()
            return 1
        raw = sys.stdin.read()

    try:
        out = refine_prompt(raw, cfg)
    except (OllamaConnectionError, OllamaResponseError) as e:
        _print_user_error(e)
        return 2

    print(out["structured_prompt"].rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
