class PromptRefinerError(Exception):
    """Base error for prompt_refiner."""


class OllamaConnectionError(PromptRefinerError):
    """Raised when Ollama is unreachable or network errors occur."""


class OllamaResponseError(PromptRefinerError):
    """Raised when Ollama returns a non-OK response or invalid payload."""
