from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from .errors import OllamaConnectionError, OllamaResponseError


class OllamaClient:
    """
    Minimal Ollama HTTP client (stdlib only).

    Primary endpoint:
      POST /api/chat

    Fallback endpoint (OpenAI-compatible):
      POST /v1/chat/completions

    Reliability:
    - If server isn't reachable, attempt to start: `ollama serve`
    - If model isn't present, attempt to pull: `ollama pull <model>` and retry once
    """

    _spawn_attempted: bool = False

    def __init__(self, base_url: str, timeout_s: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = int(timeout_s)

    def _install_hint(self) -> str:
        return (
            "Ollama is not installed or is not available in your PATH.\n"
            "Install Ollama from https://ollama.com, then run `ollama --version` to confirm it works."
        )

    def _ping(self) -> bool:
        # try a couple known Ollama endpoints
        for path in ("/api/version", "/api/tags"):
            url = f"{self.base_url}{path}"
            req = urllib.request.Request(url, method="GET")
            try:
                with urllib.request.urlopen(req, timeout=2) as resp:
                    _ = resp.read()
                return True
            except Exception:
                continue
        return False

    def _start_ollama_serve(self) -> None:
        if OllamaClient._spawn_attempted:
            return
        OllamaClient._spawn_attempted = True

        try:
            if sys.platform.startswith("win"):
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
            else:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except FileNotFoundError as e:
            raise OllamaConnectionError(self._install_hint()) from e
        except Exception as e:
            raise OllamaConnectionError(
                f"Could not start Ollama automatically.\n"
                f"Please run `ollama serve` in another terminal and try again.\n"
                f"Details: {e}"
            ) from e

    def _ensure_running(self) -> None:
        if self._ping():
            return

        self._start_ollama_serve()

        for _ in range(20):
            if self._ping():
                return
            time.sleep(0.25)

        raise OllamaConnectionError(
            f"Could not connect to Ollama at {self.base_url}.\n"
            "What to check:\n"
            "- Run `ollama serve` in a terminal\n"
            "- Verify `ollama --version` works\n"
            f"- Confirm `--ollama-url` is correct (current: {self.base_url})"
        )

    def _pull_model(self, model: str) -> None:
        print(f"Pulling Ollama model: {model}...", file=sys.stderr)
        try:
            proc = subprocess.run(
                ["ollama", "pull", model],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as e:
            raise OllamaConnectionError(self._install_hint()) from e
        except Exception as e:
            raise OllamaResponseError(
                f"Could not pull model `{model}`.\n"
                "Please run `ollama pull <model>` manually and try again.\n"
                f"Details: {e}"
            ) from e

        output = (proc.stdout or "").strip()
        if output:
            print(output, file=sys.stderr)

        if proc.returncode != 0:
            msg = output or "Unknown error."
            raise OllamaResponseError(
                f"Could not pull model `{model}`.\n"
                f"Ollama said: {msg}"
            )

    def _http_post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            # Preserve status code for logic (404 fallback)
            body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise OllamaResponseError(
                f"Ollama returned HTTP {e.code} for {url}.\n"
                f"Response: {body[:200]}"
            ) from e
        except urllib.error.URLError as e:
            raise OllamaConnectionError(
                f"Could not connect to Ollama at {self.base_url}.\n"
                "Please make sure Ollama is running and the URL is correct.\n"
                f"Details: {e}"
            ) from e

        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise OllamaResponseError(
                f"Ollama returned an unexpected response format from {url}.\n"
                f"Response preview: {body[:300]}"
            ) from e

    def list_models(self) -> list[str]:
        self._ensure_running()
        url = f"{self.base_url}/api/tags"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
            raise OllamaResponseError(
                f"Could not list models from Ollama (HTTP {e.code}).\n"
                f"Response: {msg[:200]}"
            ) from e
        except urllib.error.URLError as e:
            raise OllamaConnectionError(
                f"Could not connect to Ollama at {self.base_url}.\n"
                "Please make sure Ollama is running and the URL is correct.\n"
                f"Details: {e}"
            ) from e

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as e:
            raise OllamaResponseError(
                "Ollama returned unreadable data while listing models."
            ) from e

        models = parsed.get("models")
        if not isinstance(models, list):
            raise OllamaResponseError(
                "Ollama returned an unexpected model list format."
            )

        names: list[str] = []
        for m in models:
            if isinstance(m, dict) and isinstance(m.get("name"), str) and m["name"].strip():
                names.append(m["name"].strip())
        return names

    def _model_available(self, model: str) -> bool:
        wanted = model.strip()
        if not wanted:
            return False
        installed = self.list_models()
        if wanted in installed:
            return True
        # Ollama often resolves untagged names to :latest.
        if ":" not in wanted and f"{wanted}:latest" in installed:
            return True
        return False

    def _chat_api_chat(self, *, model: str, system: str, user: str, temperature: float) -> str:
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "stream": False,
            "options": {"temperature": float(temperature)},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        parsed = self._http_post_json(url, payload)
        if isinstance(parsed.get("error"), str) and parsed["error"].strip():
            raise OllamaResponseError(parsed["error"].strip())

        msg = parsed.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError(
                "Ollama returned an empty response for /api/chat."
            )
        return content

    def _chat_api_generate(self, *, model: str, system: str, user: str, temperature: float) -> str:
        url = f"{self.base_url}/api/generate"
        payload: Dict[str, Any] = {
            "model": model,
            "stream": False,
            "system": system,
            "prompt": user,
            "options": {"temperature": float(temperature)},
        }
        parsed = self._http_post_json(url, payload)
        if isinstance(parsed.get("error"), str) and parsed["error"].strip():
            raise OllamaResponseError(parsed["error"].strip())

        content = parsed.get("response")
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError(
                "Ollama returned an empty response for /api/generate."
            )
        return content

    def _chat_openai_compat(self, *, model: str, system: str, user: str, temperature: float) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": float(temperature),
        }
        parsed = self._http_post_json(url, payload)
        if isinstance(parsed.get("error"), dict):
            msg = parsed["error"].get("message") or str(parsed["error"])
            raise OllamaResponseError(str(msg))

        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OllamaResponseError(
                "Ollama returned no choices from /v1/chat/completions."
            )
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError(
                "Ollama returned an empty message from /v1/chat/completions."
            )
        return content

    def chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
    ) -> str:
        self._ensure_running()
        if not self._model_available(model):
            self._pull_model(model)

        try:
            return self._chat_api_chat(model=model, system=system, user=user, temperature=temperature)
        except OllamaResponseError as e:
            msg = str(e).lower()

            if "http 404" in msg and "/api/chat" in msg:
                try:
                    return self._chat_api_generate(model=model, system=system, user=user, temperature=temperature)
                except OllamaResponseError:
                    try:
                        return self._chat_openai_compat(model=model, system=system, user=user, temperature=temperature)
                    except OllamaResponseError:
                        raise OllamaResponseError(
                            f"The server at {self.base_url} does not expose Ollama chat endpoints.\n"
                            "Make sure `--ollama-url` points to a running Ollama server\n"
                            "(default: http://localhost:11434)."
                        )

            if ("not found" in msg and "model" in msg) or ("pull" in msg and "model" in msg) or ("not downloaded" in msg):
                self._pull_model(model)
                try:
                    return self._chat_api_chat(model=model, system=system, user=user, temperature=temperature)
                except OllamaResponseError:
                    return self._chat_openai_compat(model=model, system=system, user=user, temperature=temperature)

            raise
