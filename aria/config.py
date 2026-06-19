"""Application configuration as structured dataclasses."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CrsConfig:
    """Coordinate reference system settings."""

    projected: int = 32719  # UTM zone 19S — meters
    geographic: int = 4326  # WGS84 — display


@dataclass(frozen=True)
class MapConfig:
    """Default map display settings."""

    center: tuple[float, float] = (-33.45, -70.65)
    zoom: int = 11


@dataclass(frozen=True)
class SpatialConfig:
    """Thresholds for spatial calculations."""

    min_points: int = 5
    stable_threshold: float = 0.70
    partial_threshold: float = 0.30


@dataclass(frozen=True)
class CoordinateBounds:
    """Valid coordinate range for data filtering."""

    lat_range: tuple[float, float] = (-56.0, -17.0)
    lon_range: tuple[float, float] = (-76.0, -66.0)


_ROOT = os.path.dirname(os.path.dirname(__file__))


@dataclass(frozen=True)
class AppConfig:
    """Root configuration for the ARIA application."""

    data_dir: str = field(default_factory=lambda: os.path.join(_ROOT, "data"))
    crs: CrsConfig = field(default_factory=CrsConfig)
    map: MapConfig = field(default_factory=MapConfig)
    spatial: SpatialConfig = field(default_factory=SpatialConfig)
    bounds: CoordinateBounds = field(default_factory=CoordinateBounds)

    normalization_map: dict[str, str] = field(default_factory=lambda: {
        "robo a vehiculo":       "Robo a vehículo",
        "robo vehiculo":         "Robo a vehículo",
        "robo auto":             "Robo a vehículo",
        "robo casa":             "Robo en casa",
        "robo en casa":          "Robo en casa",
        "robo habitacion":       "Robo en casa",
        "robo con violencia":    "Robo con violencia",
        "robo con intimidacion": "Robo con violencia",
        "robo comercio":         "Robo en comercio",
        "robo en comercio":      "Robo en comercio",
        "hurto":                 "Hurto",
        "danos":                 "Daños",
        "daños":                 "Daños",
        "lesiones":              "Lesiones",
        "Lesiones":              "Lesiones",
        "receptacion":           "Receptación",
        "receptación":           "Receptación",
        "Receptación":           "Receptación",
        "asalto via publica":    "Asalto en la vía pública",
        "asalto en la via":      "Asalto en la vía pública",
        "asalto vía pública":    "Asalto en la vía pública",
    })

    valid_crime_types: tuple[str, ...] = (
        "Robo a vehículo",
        "Robo en casa",
        "Robo con violencia",
        "Robo en comercio",
        "Hurto",
        "Daños",
        "Lesiones",
        "Receptación",
        "Asalto en la vía pública",
        "Otro",
    )

    month_names: dict[str, int] = field(default_factory=lambda: {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    })

    crime_type_colors: dict[str, str] = field(default_factory=lambda: {
        "Robo a vehículo":          "#4f8ef7",
        "Robo en casa":             "#f75f5f",
        "Robo con violencia":       "#f7b84f",
        "Robo en comercio":         "#4fcc8e",
        "Hurto":                    "#7c5cfc",
        "Daños":                    "#f75fc8",
        "Lesiones":                 "#c74d3f",
        "Receptación":              "#5a8fa8",
        "Asalto en la vía pública": "#cc4fcc",
        "Otro":                     "#8b91b0",
    })

    ellipse_current_color: str = "#4f8ef7"
    ellipse_previous_color: str = "#f75f5f"
    trajectory_color: str = "#f7b84f"

    @property
    def geojson_path(self) -> str:
        return os.path.join(self.data_dir, "comunas_santiago.geojson")
