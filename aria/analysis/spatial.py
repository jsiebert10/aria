"""Spatial analysis: SDE, KDE, displacement, Jaccard overlap."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from shapely.geometry import Point, Polygon

from aria.config import AppConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class EllipseResult:
    """Standard Deviational Ellipse calculation result."""

    polygon: Polygon
    semi_major_m: float
    semi_minor_m: float
    rotation_degrees: float
    center: tuple[float, float]  # (lat, lon) WGS84


@dataclass(frozen=True)
class DisplacementResult:
    """Displacement between two mean centers."""

    distance_m: float
    distance_km: float
    azimuth_degrees: float
    direction: str  # N/NE/E/SE/S/SW/W/NW


@dataclass(frozen=True)
class KdeResult:
    """Kernel density estimation result."""

    lats: np.ndarray  # 2D grid
    lons: np.ndarray  # 2D grid
    density: np.ndarray  # 2D, normalized 0-1


class SpatialAnalyzer:
    """Stateless spatial calculation engine.

    Receives DataFrames as arguments, returns typed result objects.
    Uses AppConfig for CRS codes and thresholds.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    def mean_center(self, df: pd.DataFrame) -> tuple[float, float] | None:
        """Compute the mean center of a point set. Returns (lat, lon) WGS84."""
        if df is None or len(df) < 1:
            return None

        gdf = self._to_geodataframe(df)
        cx = gdf.geometry.x.mean()
        cy = gdf.geometry.y.mean()

        point = gpd.GeoDataFrame(
            geometry=[Point(cx, cy)],
            crs=f"EPSG:{self._config.crs.projected}",
        ).to_crs(epsg=self._config.crs.geographic)

        return (point.geometry.y.iloc[0], point.geometry.x.iloc[0])

    def standard_deviational_ellipse(
        self, df: pd.DataFrame,
    ) -> EllipseResult | None:
        """Compute the Standard Deviational Ellipse (64-vertex polygon in WGS84)."""
        min_pts = self._config.spatial.min_points
        if df is None or len(df) < min_pts:
            return None

        gdf = self._to_geodataframe(df)
        coords = np.column_stack([gdf.geometry.x, gdf.geometry.y])

        cx, cy = coords.mean(axis=0)
        dx = coords[:, 0] - cx
        dy = coords[:, 1] - cy
        n = len(coords)

        cov = np.array([
            [np.sum(dx**2) / n, np.sum(dx * dy) / n],
            [np.sum(dx * dy) / n, np.sum(dy**2) / n],
        ])

        eigenvalues, eigenvectors = np.linalg.eigh(cov)

        idx_major = np.argmax(eigenvalues)
        idx_minor = 1 - idx_major
        semi_major = float(np.sqrt(eigenvalues[idx_major]))
        semi_minor = float(np.sqrt(eigenvalues[idx_minor]))

        vx, vy = eigenvectors[:, idx_major]
        angle_rad = np.arctan2(vy, vx)
        angle_deg = float(np.degrees(angle_rad))

        theta = np.linspace(0, 2 * np.pi, 64)
        x_ell = semi_major * np.cos(theta)
        y_ell = semi_minor * np.sin(theta)

        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        x_rot = cx + x_ell * cos_a - y_ell * sin_a
        y_rot = cy + x_ell * sin_a + y_ell * cos_a

        crs_proj = f"EPSG:{self._config.crs.projected}"
        crs_geo = self._config.crs.geographic

        vertices_gdf = gpd.GeoDataFrame(
            geometry=[Point(x, y) for x, y in zip(x_rot, y_rot)],
            crs=crs_proj,
        ).to_crs(epsg=crs_geo)
        vertices = [(g.x, g.y) for g in vertices_gdf.geometry]
        polygon = Polygon(vertices)

        center_gdf = gpd.GeoDataFrame(
            geometry=[Point(cx, cy)], crs=crs_proj,
        ).to_crs(epsg=crs_geo)
        center_lat = float(center_gdf.geometry.y.iloc[0])
        center_lon = float(center_gdf.geometry.x.iloc[0])

        return EllipseResult(
            polygon=polygon,
            semi_major_m=semi_major,
            semi_minor_m=semi_minor,
            rotation_degrees=angle_deg,
            center=(center_lat, center_lon),
        )

    def kernel_density(
        self, df: pd.DataFrame, grid_resolution: int = 80,
    ) -> KdeResult | None:
        """Compute kernel density estimation over a geographic grid."""
        if df is None or len(df) < self._config.spatial.min_points:
            return None

        lats = df["latitud"].values
        lons = df["longitud"].values
        n = len(lats)

        bw = "scott" if n <= 500 else "silverman"
        try:
            kde = gaussian_kde(np.vstack([lons, lats]), bw_method=bw)
        except Exception as exc:
            log.error("KDE computation failed: %s", exc)
            return None

        margin = 0.02
        lon_grid = np.linspace(lons.min() - margin, lons.max() + margin, grid_resolution)
        lat_grid = np.linspace(lats.min() - margin, lats.max() + margin, grid_resolution)
        LON, LAT = np.meshgrid(lon_grid, lat_grid)

        positions = np.vstack([LON.ravel(), LAT.ravel()])
        density = kde(positions).reshape(LON.shape)

        d_min, d_max = density.min(), density.max()
        if d_max > d_min:
            density = (density - d_min) / (d_max - d_min)

        return KdeResult(lats=LAT, lons=LON, density=density)

    def displacement(
        self,
        center_prev: tuple[float, float] | None,
        center_curr: tuple[float, float] | None,
    ) -> DisplacementResult | None:
        """Distance and azimuth between two mean centers (WGS84 input)."""
        if center_prev is None or center_curr is None:
            return None

        x0, y0 = self._wgs84_to_utm(*center_prev)
        x1, y1 = self._wgs84_to_utm(*center_curr)

        dx = x1 - x0
        dy = y1 - y0
        dist = float(np.sqrt(dx**2 + dy**2))

        azimuth = float((np.degrees(np.arctan2(dx, dy)) + 360) % 360)

        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((azimuth + 22.5) / 45) % 8

        return DisplacementResult(
            distance_m=round(dist, 1),
            distance_km=round(dist / 1000, 2),
            azimuth_degrees=round(azimuth, 1),
            direction=directions[idx],
        )

    def jaccard_overlap(
        self,
        ellipse_a: EllipseResult | None,
        ellipse_b: EllipseResult | None,
    ) -> float | None:
        """Jaccard index between two SDE polygons. Returns 0-1 or None."""
        if ellipse_a is None or ellipse_b is None:
            return None
        try:
            intersection = ellipse_a.polygon.intersection(ellipse_b.polygon).area
            union = ellipse_a.polygon.union(ellipse_b.polygon).area
            if union == 0:
                return None
            return round(intersection / union, 4)
        except Exception as exc:
            log.error("Jaccard overlap failed: %s", exc)
            return None

    def classify_overlap(self, jaccard: float | None) -> str:
        """Classify Jaccard index into a descriptive category."""
        if jaccard is None:
            return "Sin datos suficientes"
        if jaccard >= self._config.spatial.stable_threshold:
            return "Patrón estable"
        if jaccard >= self._config.spatial.partial_threshold:
            return "Desplazamiento parcial"
        return "Desplazamiento significativo"

    def area_variation(
        self,
        ellipse_current: EllipseResult | None,
        ellipse_previous: EllipseResult | None,
    ) -> float | None:
        """Percentage change in ellipse area. Positive = expansion."""
        if ellipse_current is None or ellipse_previous is None:
            return None
        area_curr = ellipse_current.polygon.area
        area_prev = ellipse_previous.polygon.area
        if area_prev == 0:
            return None
        return round((area_curr - area_prev) / area_prev * 100, 1)

    # -- Private helpers -----------------------------------------------------

    def _to_geodataframe(self, df: pd.DataFrame) -> gpd.GeoDataFrame:
        """Convert DataFrame with lat/lon to projected GeoDataFrame."""
        gdf = gpd.GeoDataFrame(
            df.copy(),
            geometry=gpd.points_from_xy(df["longitud"], df["latitud"]),
            crs=f"EPSG:{self._config.crs.geographic}",
        )
        return gdf.to_crs(epsg=self._config.crs.projected)

    def _wgs84_to_utm(self, lat: float, lon: float) -> tuple[float, float]:
        """Convert a single WGS84 point to projected coordinates."""
        gdf = gpd.GeoDataFrame(
            geometry=[Point(lon, lat)],
            crs=f"EPSG:{self._config.crs.geographic}",
        ).to_crs(epsg=self._config.crs.projected)
        return float(gdf.geometry.x.iloc[0]), float(gdf.geometry.y.iloc[0])
