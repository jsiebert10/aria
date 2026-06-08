# =============================================================================
# calculos.py — Métricas espaciales de movilidad delictual
# Todos los cálculos internos en EPSG:32719 (metros).
# Las funciones devuelven geometrías y coordenadas en WGS84 (EPSG:4326).
# =============================================================================

import numpy as np
import logging
import warnings
from shapely.geometry import Point, Polygon
import geopandas as gpd
import pandas as pd
from scipy.stats import gaussian_kde
from config import EPSG_CALCULO, EPSG_MAPA, MIN_PUNTOS_CALCULO, UMBRAL_ESTABLE, UMBRAL_PARCIAL

log = logging.getLogger(__name__)


def _a_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Convierte DataFrame con latitud/longitud a GeoDataFrame en EPSG:32719."""
    gdf = gpd.GeoDataFrame(
        df.copy(),
        geometry=gpd.points_from_xy(df["longitud"], df["latitud"]),
        crs=f"EPSG:{EPSG_MAPA}"
    )
    return gdf.to_crs(epsg=EPSG_CALCULO)


def calcular_centro_medio(df_periodo: pd.DataFrame) -> tuple[float, float] | None:
    """
    Calcula el centroide del conjunto de puntos del período.
    Retorna (latitud, longitud) en WGS84 o None si no hay datos.
    """
    if df_periodo is None or len(df_periodo) < 1:
        return None

    gdf = _a_geodataframe(df_periodo)
    cx = gdf.geometry.x.mean()
    cy = gdf.geometry.y.mean()

    # Convertir punto proyectado de vuelta a WGS84
    punto = gpd.GeoDataFrame(
        geometry=[Point(cx, cy)], crs=f"EPSG:{EPSG_CALCULO}"
    ).to_crs(epsg=EPSG_MAPA)

    lon = punto.geometry.x.iloc[0]
    lat = punto.geometry.y.iloc[0]
    return (lat, lon)


def calcular_sde(df_periodo: pd.DataFrame) -> dict | None:
    """
    Calcula la Elipse de Desviación Estándar (Standard Deviational Ellipse).
    Implementación desde cero con numpy en EPSG:32719.

    Retorna dict con:
      - poligono: Shapely Polygon en WGS84 (64 vértices)
      - semieje_mayor_m: float (metros)
      - semieje_menor_m: float (metros)
      - angulo_grados: float (ángulo de rotación respecto al norte)
      - centro: (lat, lon) en WGS84
    O None si n < MIN_PUNTOS_CALCULO.
    """
    if df_periodo is None or len(df_periodo) < MIN_PUNTOS_CALCULO:
        log.warning(f"SDE: n={len(df_periodo) if df_periodo is not None else 0} "
                    f"< {MIN_PUNTOS_CALCULO}. No se calcula.")
        return None

    gdf = _a_geodataframe(df_periodo)
    coords = np.column_stack([gdf.geometry.x, gdf.geometry.y])

    # Centro medio
    cx, cy = coords.mean(axis=0)

    # Desviaciones respecto al centro
    dx = coords[:, 0] - cx
    dy = coords[:, 1] - cy
    n  = len(coords)

    # Matriz de covarianza ponderada
    cov = np.array([
        [np.sum(dx**2) / n, np.sum(dx * dy) / n],
        [np.sum(dx * dy) / n, np.sum(dy**2) / n]
    ])

    # Eigenvalores y eigenvectores
    eigenvalores, eigenvectores = np.linalg.eigh(cov)

    # Semiejes = raíz de eigenvalores (en metros)
    idx_mayor = np.argmax(eigenvalores)
    idx_menor = 1 - idx_mayor

    semieje_mayor = np.sqrt(eigenvalores[idx_mayor])
    semieje_menor = np.sqrt(eigenvalores[idx_menor])

    # Eigenvector del eje mayor → ángulo de rotación
    vx, vy = eigenvectores[:, idx_mayor]
    angulo_rad  = np.arctan2(vy, vx)
    angulo_grad = np.degrees(angulo_rad)

    # Construir elipse como polígono de 64 vértices en sistema proyectado
    theta = np.linspace(0, 2 * np.pi, 64)
    x_elipse = semieje_mayor * np.cos(theta)
    y_elipse = semieje_menor * np.sin(theta)

    # Rotar
    cos_a, sin_a = np.cos(angulo_rad), np.sin(angulo_rad)
    x_rot = cx + x_elipse * cos_a - y_elipse * sin_a
    y_rot = cy + x_elipse * sin_a + y_elipse * cos_a

    # Convertir vértices de vuelta a WGS84
    puntos_gdf = gpd.GeoDataFrame(
        geometry=[Point(x, y) for x, y in zip(x_rot, y_rot)],
        crs=f"EPSG:{EPSG_CALCULO}"
    ).to_crs(epsg=EPSG_MAPA)

    vertices_wgs84 = [(g.x, g.y) for g in puntos_gdf.geometry]
    poligono = Polygon(vertices_wgs84)

    # Centro en WGS84
    centro_gdf = gpd.GeoDataFrame(
        geometry=[Point(cx, cy)], crs=f"EPSG:{EPSG_CALCULO}"
    ).to_crs(epsg=EPSG_MAPA)
    centro_lat = centro_gdf.geometry.y.iloc[0]
    centro_lon = centro_gdf.geometry.x.iloc[0]

    return {
        "poligono":       poligono,
        "semieje_mayor_m": semieje_mayor,
        "semieje_menor_m": semieje_menor,
        "angulo_grados":   angulo_grad,
        "centro":          (centro_lat, centro_lon),
    }


def calcular_kde(df_periodo: pd.DataFrame, grilla_resolucion: int = 80) -> dict | None:
    """
    Calcula densidad de kernel (KDE) para el período.
    Usa scipy.stats.gaussian_kde con bandwidth 'scott' (n<=500) o 'silverman'.

    Retorna dict con:
      - lats: array 2D de latitudes de la grilla
      - lons: array 2D de longitudes de la grilla
      - densidad: array 2D de valores de densidad (normalizado 0-1)
    O None si n < MIN_PUNTOS_CALCULO.
    """
    if df_periodo is None or len(df_periodo) < MIN_PUNTOS_CALCULO:
        return None

    lats = df_periodo["latitud"].values
    lons = df_periodo["longitud"].values
    n    = len(lats)

    bw = "scott" if n <= 500 else "silverman"

    try:
        kde = gaussian_kde(np.vstack([lons, lats]), bw_method=bw)
    except Exception as e:
        log.error(f"KDE: error al calcular → {e}")
        return None

    # Grilla sobre el bounding box de los puntos con margen
    margen = 0.02
    lon_min, lon_max = lons.min() - margen, lons.max() + margen
    lat_min, lat_max = lats.min() - margen, lats.max() + margen

    lon_grid = np.linspace(lon_min, lon_max, grilla_resolucion)
    lat_grid = np.linspace(lat_min, lat_max, grilla_resolucion)
    LON, LAT = np.meshgrid(lon_grid, lat_grid)

    posiciones = np.vstack([LON.ravel(), LAT.ravel()])
    densidad = kde(posiciones).reshape(LON.shape)

    # Normalizar a 0-1
    d_min, d_max = densidad.min(), densidad.max()
    if d_max > d_min:
        densidad = (densidad - d_min) / (d_max - d_min)

    return {
        "lats":     LAT,
        "lons":     LON,
        "densidad": densidad,
    }


def calcular_desplazamiento(
    centro_t: tuple[float, float],
    centro_t1: tuple[float, float]
) -> dict | None:
    """
    Distancia y azimut entre dos centros medios consecutivos.
    Cálculo en EPSG:32719 (metros).

    Retorna dict con:
      - distancia_m: float
      - distancia_km: float
      - azimut_grados: float (0=Norte, 90=Este, etc.)
      - direccion: str (N/NE/E/SE/S/SW/W/NW)
    O None si algún centro es None.
    """
    if centro_t is None or centro_t1 is None:
        return None

    def wgs84_a_utm(lat, lon):
        gdf = gpd.GeoDataFrame(
            geometry=[Point(lon, lat)], crs=f"EPSG:{EPSG_MAPA}"
        ).to_crs(epsg=EPSG_CALCULO)
        return gdf.geometry.x.iloc[0], gdf.geometry.y.iloc[0]

    x0, y0 = wgs84_a_utm(*centro_t)
    x1, y1 = wgs84_a_utm(*centro_t1)

    dx = x1 - x0
    dy = y1 - y0
    distancia = np.sqrt(dx**2 + dy**2)

    # Azimut: 0° = Norte, clockwise
    azimut = (np.degrees(np.arctan2(dx, dy)) + 360) % 360

    # Clasificar dirección en 8 puntos cardinales
    puntos = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((azimut + 22.5) / 45) % 8

    return {
        "distancia_m":   round(distancia, 1),
        "distancia_km":  round(distancia / 1000, 2),
        "azimut_grados": round(azimut, 1),
        "direccion":     puntos[idx],
    }


def calcular_solapamiento(elipse_t: dict | None, elipse_t1: dict | None) -> float | None:
    """
    Índice de Jaccard entre dos elipses SDE (polígonos shapely).
    Retorna float 0–1 o None si alguna elipse es None.
    """
    if elipse_t is None or elipse_t1 is None:
        return None

    pol_a = elipse_t["poligono"]
    pol_b = elipse_t1["poligono"]

    try:
        interseccion = pol_a.intersection(pol_b).area
        union        = pol_a.union(pol_b).area
        if union == 0:
            return None
        return round(interseccion / union, 4)
    except Exception as e:
        log.error(f"Solapamiento: error → {e}")
        return None


def clasificar_solapamiento(indice: float | None) -> str:
    """
    Clasifica el índice de Jaccard en categoría descriptiva.
    """
    if indice is None:
        return "Sin datos suficientes"
    if indice >= UMBRAL_ESTABLE:
        return "Patrón estable"
    if indice >= UMBRAL_PARCIAL:
        return "Desplazamiento parcial"
    return "Desplazamiento significativo"


def calcular_variacion_area(elipse_t: dict | None, elipse_t1: dict | None) -> float | None:
    """
    Variación porcentual del área de la elipse respecto al período anterior.
    Positivo = expansión, Negativo = contracción.
    Retorna float (%) o None.
    """
    if elipse_t is None or elipse_t1 is None:
        return None
    area_actual   = elipse_t["poligono"].area
    area_anterior = elipse_t1["poligono"].area
    if area_anterior == 0:
        return None
    return round((area_actual - area_anterior) / area_anterior * 100, 1)
