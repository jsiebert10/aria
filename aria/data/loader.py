"""Data loading, validation, and normalization from monthly Excel/CSV files."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from aria.config import AppConfig

log = logging.getLogger(__name__)


class DataLoader:
    """Loads and normalizes monthly crime data files.

    All configuration (coordinate bounds, normalization map, month names)
    comes from the injected ``AppConfig``.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    # -- Public API ----------------------------------------------------------

    def load_all(self, data_dir: str | None = None) -> pd.DataFrame:
        """Read all .xlsx/.csv files from the data directory.

        Returns a unified DataFrame sorted chronologically with
        comuna assignments from spatial join.
        """
        target_dir = data_dir or self._config.data_dir
        files = sorted(
            f for f in os.listdir(target_dir)
            if f.endswith((".xlsx", ".csv")) and not f.startswith("~")
        )

        if not files:
            log.warning("No files found in '%s'", target_dir)
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        for filename in files:
            full_path = os.path.join(target_dir, filename)
            df = self.load_monthly_file(full_path)
            if df is not None and not df.empty:
                frames.append(df)

        if not frames:
            log.error("No valid files found.")
            return pd.DataFrame()

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.sort_values("periodo_orden").reset_index(drop=True)

        log.info(
            "Total loaded: %d records across %d period(s)",
            len(combined),
            combined["periodo_label"].nunique(),
        )

        combined["comuna"] = self.assign_comunas(combined)
        return combined

    def load_monthly_file(self, path: str) -> pd.DataFrame | None:
        """Read and normalize a single monthly Excel/CSV file."""
        filename = os.path.basename(path)
        period = self.parse_period_from_filename(filename)
        if period is None:
            return None

        month_num, year = period

        try:
            df_raw = (
                pd.read_csv(path, header=0)
                if path.endswith(".csv")
                else pd.read_excel(path, header=0)
            )
        except Exception as exc:
            log.error("Error reading '%s': %s", filename, exc)
            return None

        first_col = str(df_raw.columns[0]).strip().lower()
        if first_col != "fenomeno":
            df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
            df_raw = df_raw[1:].reset_index(drop=True)

        df_raw = df_raw.rename(columns=self._detect_columns(df_raw))

        required = {"fenomeno", "latitud", "longitud"}
        missing = required - set(df_raw.columns)
        if missing:
            log.error("'%s': missing columns: %s", filename, missing)
            return None

        base_cols = ["fenomeno", "latitud", "longitud"]
        extra_cols = [c for c in ("fecha", "hora") if c in df_raw.columns]
        df = df_raw[base_cols + extra_cols].copy()
        initial_count = len(df)

        df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
        df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

        lat_lo, lat_hi = self._config.bounds.lat_range
        lon_lo, lon_hi = self._config.bounds.lon_range
        valid_mask = (
            df["latitud"].notna()
            & df["longitud"].notna()
            & df["latitud"].between(lat_lo, lat_hi)
            & df["longitud"].between(lon_lo, lon_hi)
        )
        df = df[valid_mask].copy()
        discarded = initial_count - len(df)
        if discarded > 0:
            log.warning(
                "'%s': %d rows discarded (null or out-of-bounds coordinates)",
                filename, discarded,
            )

        df = df[
            df["fenomeno"].notna()
            & (df["fenomeno"].astype(str).str.strip() != "")
        ]

        df["fenomeno"] = df["fenomeno"].astype(str).apply(self.normalize_crime_type)

        month_label = self._month_number_to_name(month_num)
        df["mes"] = month_num
        df["anio"] = year
        df["periodo_label"] = f"{month_label} {year}"
        df["periodo_orden"] = year * 100 + month_num

        log.info(
            "'%s': %d valid records loaded (period %s %d)",
            filename, len(df), month_label, year,
        )
        return df

    def parse_period_from_filename(self, filename: str) -> tuple[int, int] | None:
        """Extract (month, year) from a filename like 'enero_2025.xlsx'."""
        stem = Path(filename).stem.lower().strip()
        parts = stem.replace("-", "_").split("_")

        month_num: int | None = None
        year: int | None = None

        for part in parts:
            if part in self._config.month_names:
                month_num = self._config.month_names[part]
            elif re.match(r"^\d{4}$", part):
                year = int(part)

        if month_num and year:
            return (month_num, year)

        log.warning(
            "Could not parse period from '%s'. Expected: enero_2025.xlsx",
            filename,
        )
        return None

    def normalize_crime_type(self, value: str) -> str:
        """Normalize a raw crime type string to its canonical form."""
        if not isinstance(value, str) or not value.strip():
            return "Otro"

        clean = value.strip().lower()
        clean_no_accents = (
            clean
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ü", "u")
        )

        norm_map = self._config.normalization_map
        if clean in norm_map:
            return norm_map[clean]
        if clean_no_accents in norm_map:
            return norm_map[clean_no_accents]

        for key, canonical in norm_map.items():
            if key in clean_no_accents or clean_no_accents in key:
                return canonical

        title = value.strip().title()
        if title in self._config.valid_crime_types:
            return title

        log.warning("Unrecognized crime type: '%s' → assigned to 'Otro'", value)
        return "Otro"

    def assign_comunas(
        self,
        df: pd.DataFrame,
        geojson_path: str | None = None,
    ) -> pd.Series:
        """Assign comuna to each point via spatial join.

        Strategy: 'within' first, nearest-neighbor fallback for full coverage.
        """
        target_path = geojson_path or self._config.geojson_path

        if not os.path.exists(target_path):
            log.warning("Comuna GeoJSON not found. 'comuna' column unassigned.")
            return pd.Series([None] * len(df), index=df.index)

        crs_geo = f"EPSG:{self._config.crs.geographic}"
        crs_proj = self._config.crs.projected

        gdf_com = (
            gpd.read_file(target_path)
            .set_crs(epsg=self._config.crs.geographic)
            .to_crs(epsg=crs_proj)
        )

        gdf_pts = gpd.GeoDataFrame(
            {"_pos": range(len(df))},
            geometry=gpd.points_from_xy(df["longitud"], df["latitud"]),
            crs=crs_geo,
        ).to_crs(epsg=crs_proj)

        join = gpd.sjoin(
            gdf_pts, gdf_com[["comuna", "geometry"]],
            how="left", predicate="within",
        )
        join = join[~join.index.duplicated(keep="first")]
        comunas = join["comuna"].copy()

        unmatched = comunas[comunas.isna()].index.tolist()
        if unmatched:
            pts_unmatched = gdf_pts.loc[unmatched]
            nearest = gpd.sjoin_nearest(
                pts_unmatched, gdf_com[["comuna", "geometry"]], how="left",
            )
            nearest = nearest[~nearest.index.duplicated(keep="first")]
            comunas.loc[unmatched] = nearest["comuna"].values

        result = pd.Series(comunas.values, index=df.index)
        log.info("Comunas assigned: %d/%d points", result.notna().sum(), len(result))
        return result

    # -- Private helpers -----------------------------------------------------

    def _month_number_to_name(self, month_num: int) -> str:
        """Convert month number to capitalized Spanish name."""
        reverse = {v: k.capitalize() for k, v in self._config.month_names.items()}
        return reverse.get(month_num, str(month_num))

    @staticmethod
    def _detect_columns(df: pd.DataFrame) -> dict[str, str]:
        """Map raw column names to standard internal names."""
        col_map: dict[str, str] = {}
        for col in df.columns:
            col_lower = str(col).lower().strip()
            if col_lower in ("fenomeno", "fenómeno", "tipo", "tipo_delito"):
                col_map[col] = "fenomeno"
            elif col_lower.endswith(".latitud") or col_lower == "latitud":
                col_map[col] = "latitud"
            elif col_lower.endswith(".longitud") or col_lower == "longitud":
                col_map[col] = "longitud"
            elif col_lower in ("fecha", "date", "fecha_hecho"):
                col_map[col] = "fecha"
            elif col_lower in ("hora", "time", "hora_hecho", "hora_ocurrencia"):
                col_map[col] = "hora"
            elif col_lower in ("comuna", "nombre_comuna"):
                col_map[col] = "comuna_raw"
        return col_map
