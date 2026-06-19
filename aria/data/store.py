"""Central read-only data container for the ARIA application."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)


@dataclass
class DataStore:
    """Holds all loaded crime data and derived lookups.

    Created once at startup via ``DataStore.create()``.
    All modules receive a reference to the same instance.
    """

    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    periods: list[str] = field(default_factory=list)
    phenomena: list[str] = field(default_factory=list)
    comunas: list[str] = field(default_factory=lambda: ["Todas"])
    comunas_geojson: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, df: pd.DataFrame, geojson_path: str) -> DataStore:
        """Build a DataStore from a loaded DataFrame and GeoJSON path."""
        if df.empty:
            log.warning("DataStore created with empty DataFrame.")
            return cls()

        periods = (
            df[["periodo_label", "periodo_orden"]]
            .drop_duplicates()
            .sort_values("periodo_orden")["periodo_label"]
            .tolist()
        )
        phenomena = sorted(df["fenomeno"].unique().tolist())
        comunas = ["Todas"] + sorted(
            df["comuna"].dropna().unique().tolist()
        )

        geojson: dict[str, Any] = {}
        if os.path.exists(geojson_path):
            with open(geojson_path, encoding="utf-8") as f:
                geojson = json.load(f)
        else:
            log.warning("GeoJSON not found at %s", geojson_path)

        return cls(
            df=df,
            periods=periods,
            phenomena=phenomena,
            comunas=comunas,
            comunas_geojson=geojson,
        )

    @property
    def is_empty(self) -> bool:
        return self.df.empty

    @property
    def record_count(self) -> int:
        return len(self.df)

    @property
    def period_count(self) -> int:
        return len(self.periods)

    @property
    def comuna_count(self) -> int:
        """Number of comunas excluding the 'Todas' entry."""
        return len(self.comunas) - 1

    def filter_by(
        self,
        phenomenon: str | None = None,
        period: str | None = None,
        comuna: str | None = None,
    ) -> pd.DataFrame:
        """Return a filtered view of the main DataFrame."""
        result = self.df
        if phenomenon:
            result = result[result["fenomeno"] == phenomenon]
        if period:
            result = result[result["periodo_label"] == period]
        if comuna and comuna != "Todas":
            result = result[result["comuna"] == comuna]
        return result
