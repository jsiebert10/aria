"""Abstract base class for all ARIA dashboard modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from dash import Dash, html

if TYPE_CHECKING:
    from aria.data.store import DataStore
    from aria.theme import Theme


class BaseModule(ABC):
    """Standard interface for ARIA dashboard modules.

    Every module receives the same core dependencies via constructor
    and exposes a two-phase lifecycle:
      1. ``get_layout()`` — called each time the module tab is selected
      2. ``register_callbacks(app)`` — called once at startup
    """

    module_id: str = ""
    display_name: str = ""

    def __init__(self, store: DataStore, theme: Theme) -> None:
        self._store = store
        self._theme = theme

    @abstractmethod
    def get_layout(self) -> html.Div:
        """Return the Dash component tree for this module."""
        ...

    @abstractmethod
    def register_callbacks(self, app: Dash) -> None:
        """Register all Dash callbacks on the app instance."""
        ...
