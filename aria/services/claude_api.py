"""Shared Claude API client for ARIA AI features."""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


class ClaudeApiClient:
    """Thin wrapper around the Anthropic SDK.

    Centralizes API key loading, error handling, and model selection.
    Shared by CaseGrouperModule and PolicyBriefModule.
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_MAX_TOKENS = 2048

    def __init__(self, env_path: str | None = None) -> None:
        self._api_key: str | None = None
        self._env_path = env_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env",
        )

    def send_prompt(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a prompt to Claude and return the text response.

        Returns an error message string (never raises) on failure,
        so callers can display it directly in the UI.
        """
        self._ensure_key()
        if not self._api_key or self._api_key == "tu_api_key_aqui":
            return (
                "⚠ API key no configurada. Edita el archivo .env "
                "y agrega tu ANTHROPIC_API_KEY."
            )
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self._api_key)
            response = client.messages.create(
                model=model or self.DEFAULT_MODEL,
                max_tokens=max_tokens or self.DEFAULT_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as exc:
            log.error("Claude API error: %s", exc)
            return f"Error al conectar con Claude API: {exc}"

    def _ensure_key(self) -> None:
        """Lazy-load API key from .env on first call."""
        if self._api_key is not None:
            return
        try:
            from dotenv import load_dotenv

            load_dotenv(self._env_path)
        except ImportError:
            pass
        self._api_key = os.getenv("ANTHROPIC_API_KEY", "")
