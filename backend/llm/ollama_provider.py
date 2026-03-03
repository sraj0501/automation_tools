"""
Ollama LLM provider.

Thin wrapper over the existing backend/ai/ollama_client.py so that
module is preserved untouched (other code may import it directly).
"""

import logging
from typing import Optional

from backend.llm.base import LLMOptions, LLMProvider

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """LLM provider that dispatches to a local Ollama instance."""

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        # Lazy config load — same pattern used by ollama_client.py
        _host = host
        _model = model
        if _host is None or _model is None:
            try:
                from backend.config import ollama_host, ollama_model
                _host = _host or ollama_host()
                _model = _model or ollama_model()
            except Exception:
                _host = _host or "http://localhost:11434"
                _model = _model or "llama3.2"
        self._host = _host
        self._model = _model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        try:
            from backend.ai.ollama_client import is_available
            return is_available(self._host)
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        options: Optional[LLMOptions] = None,
        timeout: int = 30,
    ) -> Optional[str]:
        try:
            from backend.ai.ollama_client import generate
            opts = options or LLMOptions()
            return generate(
                prompt=prompt,
                model=self._model,
                host=self._host,
                options={"temperature": opts.temperature, "num_predict": opts.max_tokens, **opts.extra},
                timeout=timeout,
            )
        except Exception as e:
            logger.warning(f"OllamaProvider.generate failed: {e}")
            return None
