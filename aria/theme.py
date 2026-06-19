"""Unified SIRAC theme: colors, fonts, and Plotly layout helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import plotly.graph_objects as go


@dataclass(frozen=True)
class Theme:
    """Single source of truth for the ARIA visual language.

    All color values and plot layout defaults live here.
    Modules never define their own color constants.
    """

    # Background hierarchy (darkest to lightest)
    bg: str = "#0a0e14"
    bg1: str = "#10161e"
    bg2: str = "#161d27"
    bg3: str = "#1c2530"

    # Borders
    border: str = "#26303d"
    border_soft: str = "#1e2732"

    # Text hierarchy (brightest to dimmest)
    text: str = "#e8e6d9"
    text2: str = "#a8adb5"
    text3: str = "#6b727d"

    # Semantic accent colors
    amber: str = "#d4a84b"
    amber2: str = "#b38a2e"
    amber_glow: str = "rgba(212,168,75,.12)"
    danger: str = "#c74d3f"
    warning: str = "#d49b3f"
    success: str = "#7a9e6c"
    info: str = "#5a8fa8"

    # Fonts
    font_sans: str = "IBM Plex Sans,sans-serif"
    font_mono: str = "IBM Plex Mono,monospace"
    font_serif: str = "Fraunces,Georgia,serif"

    # Sequential palette for chart series
    series_colors: tuple[str, ...] = (
        "#d4a84b", "#c74d3f", "#5a8fa8", "#7a9e6c",
        "#d49b3f", "#7c5cfc", "#f75fc8", "#5cf7e8", "#cc4fcc",
    )

    def plot_base(
        self,
        margin: dict[str, int] | None = None,
        no_axes: bool = False,
    ) -> dict[str, Any]:
        """Base Plotly layout dict shared across all modules."""
        m = margin or {"l": 40, "r": 12, "t": 8, "b": 32}
        layout: dict[str, Any] = {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": self.text2, "size": 10, "family": self.font_sans},
            "margin": m,
        }
        if not no_axes:
            axis = {"gridcolor": self.border, "showline": False, "zeroline": False}
            layout["xaxis"] = dict(axis)
            layout["yaxis"] = dict(axis)
        return layout

    def empty_figure(self, message: str = "Sin datos") -> go.Figure:
        """Consistent empty-state figure with centered annotation."""
        fig = go.Figure(layout=go.Layout(**self.plot_base()))
        fig.add_annotation(
            text=message, x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font={"color": self.text3, "size": 11},
        )
        return fig

    def classify_color(self, jaccard: float | None) -> str:
        """Color for Jaccard overlap classification."""
        if jaccard is None:
            return self.text3
        if jaccard >= 0.70:
            return self.success
        if jaccard >= 0.30:
            return self.warning
        return self.danger

    def classify_bg(self, jaccard: float | None) -> str:
        """Background tint for Jaccard overlap classification."""
        if jaccard is None:
            return "rgba(107,114,125,.15)"
        if jaccard >= 0.70:
            return "rgba(122,158,108,.15)"
        if jaccard >= 0.30:
            return "rgba(212,155,63,.15)"
        return "rgba(199,77,63,.15)"

    def classify_label(self, jaccard: float | None) -> str:
        """Label for Jaccard overlap classification."""
        if jaccard is None:
            return "Sin datos"
        if jaccard >= 0.70:
            return "Patrón estable"
        if jaccard >= 0.30:
            return "Desp. parcial"
        return "Desp. significativo"

    def badge_style(self, badge_type: str) -> dict[str, str]:
        """CSS dict for navigation badge types (activo/dev/pronto)."""
        color_map = {
            "activo": (self.success, f"{self.success}22", f"{self.success}44"),
            "dev":    (self.info,    f"{self.info}22",    f"{self.info}44"),
            "pronto": (self.text3,   self.bg3,            self.border),
        }
        color, bg, brd = color_map.get(badge_type, color_map["pronto"])
        return {
            "background": bg, "color": color,
            "border": f"1px solid {brd}",
            "letterSpacing": ".5px",
            "fontFamily": "var(--mono)",
            "fontSize": "8px",
            "padding": "1px 5px",
        }
