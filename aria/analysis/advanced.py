"""Advanced spatial analysis: Near Repeat, NNI, Network KDE."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import norm


@dataclass(frozen=True)
class NearRepeatResult:
    """Per-radius near repeat analysis for one period."""

    period: str
    radius_m: int
    total_events: int
    near_repeat_count: int
    near_repeat_pct: float


@dataclass(frozen=True)
class NniResult:
    """Nearest Neighbor Index result (Clark & Evans 1954)."""

    r_index: float
    observed_distance_m: float
    expected_distance_m: float
    z_score: float
    p_value: float
    n: int
    interpretation: str
    significant: bool


@dataclass(frozen=True)
class NetworkKdeResult:
    """Network KDE density grid (Manhattan distance proxy)."""

    density: np.ndarray    # 2D
    lat_grid: np.ndarray   # 1D geographic
    lon_grid: np.ndarray   # 1D geographic


def _deg_to_meters(
    lat: np.ndarray,
    lon: np.ndarray,
    lat0: float = -33.45,
    lon0: float = -70.65,
) -> np.ndarray:
    """Convert geographic coordinates to approximate meters centered on Santiago."""
    dlat = (lat - lat0) * 111320
    dlon = (lon - lon0) * 111320 * np.cos(np.radians(lat0))
    return np.column_stack([dlat, dlon])


class AdvancedAnalyzer:
    """Stateless advanced spatial analysis engine."""

    @staticmethod
    def near_repeat(
        df: pd.DataFrame,
        phenomenon: str,
        periods: list[str],
        radii: list[int] | None = None,
    ) -> list[NearRepeatResult]:
        """Near Repeat Analysis across consecutive periods.

        Measures whether events in the current period have
        spatially close antecedents in the previous period.
        Ref: Johnson et al. (2007).
        """
        radii = radii or [200, 400, 600, 800, 1000]
        results: list[NearRepeatResult] = []

        df_f = df[df["fenomeno"] == phenomenon]

        for i in range(1, len(periods)):
            period_curr = periods[i]
            period_prev = periods[i - 1]
            df_curr = df_f[df_f["periodo_label"] == period_curr]
            df_prev = df_f[df_f["periodo_label"] == period_prev]

            if len(df_curr) < 5 or len(df_prev) < 5:
                continue

            pts_curr = _deg_to_meters(
                df_curr["latitud"].values, df_curr["longitud"].values,
            )
            pts_prev = _deg_to_meters(
                df_prev["latitud"].values, df_prev["longitud"].values,
            )
            tree = cKDTree(pts_prev)

            for r in radii:
                neighbors = tree.query_ball_point(pts_curr, r=r)
                n_near = sum(1 for nbrs in neighbors if len(nbrs) > 0)
                pct = round(n_near / len(pts_curr) * 100, 1)
                results.append(NearRepeatResult(
                    period=period_curr,
                    radius_m=r,
                    total_events=len(pts_curr),
                    near_repeat_count=n_near,
                    near_repeat_pct=pct,
                ))

        return results

    @staticmethod
    def nearest_neighbor_index(
        df: pd.DataFrame,
        phenomenon: str,
        period: str,
    ) -> NniResult | None:
        """Clark & Evans (1954) Nearest Neighbor Index.

        R < 1: clustering, R = 1: random, R > 1: dispersed.
        """
        df_f = df[
            (df["fenomeno"] == phenomenon)
            & (df["periodo_label"] == period)
        ]
        if len(df_f) < 10:
            return None

        pts = _deg_to_meters(df_f["latitud"].values, df_f["longitud"].values)
        n = len(pts)
        tree = cKDTree(pts)
        dists, _ = tree.query(pts, k=2)
        nn_dists = dists[:, 1]

        d_obs = float(np.mean(nn_dists))

        x_range = pts[:, 0].max() - pts[:, 0].min()
        y_range = pts[:, 1].max() - pts[:, 1].min()
        area = x_range * y_range
        if area == 0:
            return None

        d_exp = 0.5 * np.sqrt(area / n)
        r_index = d_obs / d_exp

        se = 0.26136 / np.sqrt(n * n / area)
        z = (d_obs - d_exp) / se if se > 0 else 0.0
        p = float(2 * (1 - norm.cdf(abs(z))))

        if r_index < 0.7:
            interp = "Clustering significativo"
        elif r_index < 0.9:
            interp = "Clustering moderado"
        elif r_index < 1.1:
            interp = "Distribución aleatoria"
        else:
            interp = "Distribución dispersa"

        return NniResult(
            r_index=round(float(r_index), 3),
            observed_distance_m=round(d_obs, 1),
            expected_distance_m=round(float(d_exp), 1),
            z_score=round(float(z), 2),
            p_value=round(p, 4),
            n=n,
            interpretation=interp,
            significant=p < 0.05,
        )

    @staticmethod
    def network_kde(
        df: pd.DataFrame,
        phenomenon: str,
        period: str,
        bandwidth: int = 300,
    ) -> NetworkKdeResult | None:
        """Manhattan-distance KDE as proxy for street-network density.

        Ref: Xie & Yan (2008).
        """
        df_f = df[
            (df["fenomeno"] == phenomenon)
            & (df["periodo_label"] == period)
        ]
        if len(df_f) < 5:
            return None

        pts = _deg_to_meters(df_f["latitud"].values, df_f["longitud"].values)

        n_grid = 40
        x_min = pts[:, 0].min() - bandwidth
        x_max = pts[:, 0].max() + bandwidth
        y_min = pts[:, 1].min() - bandwidth
        y_max = pts[:, 1].max() + bandwidth

        xi = np.linspace(x_min, x_max, n_grid)
        yi = np.linspace(y_min, y_max, n_grid)
        Xi, Yi = np.meshgrid(xi, yi)
        grid_pts = np.column_stack([Xi.ravel(), Yi.ravel()])

        Z = np.zeros(len(grid_pts))
        for pt in pts:
            manhattan_dist = np.abs(grid_pts[:, 0] - pt[0]) + np.abs(grid_pts[:, 1] - pt[1])
            mask = manhattan_dist <= bandwidth
            Z[mask] += (1 - manhattan_dist[mask] / bandwidth) ** 2

        Z = Z.reshape(n_grid, n_grid)

        lat0, lon0 = -33.45, -70.65
        xi_geo = xi / 111320 + lat0
        yi_geo = yi / (111320 * np.cos(np.radians(lat0))) + lon0

        return NetworkKdeResult(density=Z, lat_grid=xi_geo, lon_grid=yi_geo)
