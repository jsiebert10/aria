# =============================================================================
# ingesta.py — Carga, validación y normalización de archivos mensuales
# Formato esperado: mes_año.xlsx con columnas fenomeno, MES.latitud, MES.longitud
# =============================================================================

import os
import re
import logging
import pandas as pd
from pathlib import Path
from config import (
    RUTA_DATOS, MESES_ES, MAPA_NORMALIZACION,
    TIPOS_PENALES_VALIDOS, RANGO_LAT, RANGO_LON
)

logging.basicConfig(level=logging.INFO, format="[ingesta] %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def parsear_periodo_desde_nombre(nombre_archivo: str) -> tuple[int, int] | None:
    """
    Extrae (mes, año) desde el nombre del archivo.
    Formato esperado: enero_2025.xlsx, febrero_2025.xlsx, etc.
    Retorna (mes_int, año_int) o None si no puede parsear.
    """
    stem = Path(nombre_archivo).stem.lower().strip()  # ej: "enero_2025"
    partes = stem.replace("-", "_").split("_")

    mes_int = None
    anio_int = None

    for parte in partes:
        if parte in MESES_ES:
            mes_int = MESES_ES[parte]
        elif re.match(r"^\d{4}$", parte):
            anio_int = int(parte)

    if mes_int and anio_int:
        return (mes_int, anio_int)

    log.warning(f"No se pudo parsear período desde '{nombre_archivo}'. "
                f"Formato esperado: enero_2025.xlsx")
    return None


def normalizar_tipo_penal(valor: str) -> str:
    """
    Normaliza un string de tipo penal a la lista controlada en config.py.
    Aplica strip, lowercase y búsqueda por coincidencia parcial.
    Valores no reconocidos → 'Otro'.
    """
    if not isinstance(valor, str) or not valor.strip():
        return "Otro"

    limpio = valor.strip().lower()
    # Eliminar tildes para comparación robusta
    limpio_sin_tildes = (limpio
        .replace("á","a").replace("é","e").replace("í","i")
        .replace("ó","o").replace("ú","u").replace("ü","u"))

    # Coincidencia exacta primero
    if limpio in MAPA_NORMALIZACION:
        return MAPA_NORMALIZACION[limpio]
    if limpio_sin_tildes in MAPA_NORMALIZACION:
        return MAPA_NORMALIZACION[limpio_sin_tildes]

    # Coincidencia parcial
    for clave, canonica in MAPA_NORMALIZACION.items():
        if clave in limpio_sin_tildes or limpio_sin_tildes in clave:
            return canonica

    # Verificar si ya es una categoría válida (title case)
    title = valor.strip().title()
    if title in TIPOS_PENALES_VALIDOS:
        return title

    log.warning(f"Tipo penal no reconocido: '{valor}' → asignado a 'Otro'")
    return "Otro"


def leer_archivo_mensual(ruta: str) -> pd.DataFrame | None:
    """
    Lee un archivo Excel mensual y lo transforma al esquema interno:
    columnas: fenomeno, latitud, longitud, mes, anio, periodo_label
    
    Maneja el formato real: columnas como 'FEBRERO (2).latitud'
    """
    nombre = os.path.basename(ruta)
    periodo = parsear_periodo_desde_nombre(nombre)
    if periodo is None:
        return None

    mes_int, anio_int = periodo

    # Leer sin asumir cabecera — la primera fila es el header real
    try:
        if ruta.endswith(".csv"):
            df_raw = pd.read_csv(ruta, header=0)
        else:
            df_raw = pd.read_excel(ruta, header=0)
    except Exception as e:
        log.error(f"Error al leer '{nombre}': {e}")
        return None

    # La primera fila puede ser el header real (cuando pandas lo lee como datos)
    # Detectar si la primera fila contiene 'fenomeno' como valor
    primera_col = str(df_raw.columns[0]).strip().lower()
    if primera_col != "fenomeno":
        # El header está en la primera fila de datos
        df_raw.columns = [str(c).strip() for c in df_raw.iloc[0]]
        df_raw = df_raw[1:].reset_index(drop=True)

    # Renombrar columnas: detectar fenomeno, latitud, longitud
    # sin importar el prefijo (ej: "FEBRERO (2).latitud" → latitud)
    col_map = {}
    for col in df_raw.columns:
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

    df_raw = df_raw.rename(columns=col_map)

    # Validar columnas requeridas
    requeridas = {"fenomeno", "latitud", "longitud"}
    presentes = set(df_raw.columns)
    faltantes = requeridas - presentes
    if faltantes:
        log.error(f"'{nombre}': columnas faltantes: {faltantes}")
        return None

    # Seleccionar columnas disponibles
    cols_base = ["fenomeno", "latitud", "longitud"]
    cols_extra = [c for c in ["fecha", "hora"] if c in df_raw.columns]
    df = df_raw[cols_base + cols_extra].copy()
    n_inicial = len(df)

    # Convertir coordenadas a numérico
    df["latitud"]  = pd.to_numeric(df["latitud"],  errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

    # Eliminar filas con coordenadas nulas o fuera de Chile continental
    mask_valido = (
        df["latitud"].notna() & df["longitud"].notna() &
        df["latitud"].between(*RANGO_LAT) &
        df["longitud"].between(*RANGO_LON)
    )
    df = df[mask_valido].copy()
    n_descartados = n_inicial - len(df)
    if n_descartados > 0:
        log.warning(f"'{nombre}': {n_descartados} filas descartadas "
                    f"(coordenadas nulas o fuera de Chile)")

    # Eliminar filas sin fenomeno
    df = df[df["fenomeno"].notna() & (df["fenomeno"].astype(str).str.strip() != "")]

    # Normalizar tipo penal
    df["fenomeno"] = df["fenomeno"].astype(str).apply(normalizar_tipo_penal)

    # Agregar dimensión temporal
    meses_nombre = {v: k.capitalize() for k, v in MESES_ES.items()}
    df["mes"]           = mes_int
    df["anio"]          = anio_int
    df["periodo_label"] = f"{meses_nombre[mes_int]} {anio_int}"
    df["periodo_orden"] = anio_int * 100 + mes_int  # para ordenar cronológicamente

    log.info(f"'{nombre}': {len(df)} registros válidos cargados "
             f"(período {meses_nombre[mes_int]} {anio_int})")
    return df


def cargar_todos(ruta_datos: str = RUTA_DATOS) -> pd.DataFrame:
    """
    Lee todos los archivos .xlsx y .csv de la carpeta de datos.
    Retorna DataFrame unificado ordenado cronológicamente.
    """
    archivos = sorted([
        f for f in os.listdir(ruta_datos)
        if f.endswith((".xlsx", ".csv")) and not f.startswith("~")
    ])

    if not archivos:
        log.warning(f"No se encontraron archivos en '{ruta_datos}'")
        return pd.DataFrame()

    dfs = []
    for archivo in archivos:
        ruta_completa = os.path.join(ruta_datos, archivo)
        df = leer_archivo_mensual(ruta_completa)
        if df is not None and not df.empty:
            dfs.append(df)

    if not dfs:
        log.error("Ningún archivo válido encontrado.")
        return pd.DataFrame()

    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total.sort_values("periodo_orden").reset_index(drop=True)

    log.info(f"Total cargado: {len(df_total)} registros en "
             f"{df_total['periodo_label'].nunique()} período(s)")

    # Asignar comuna a todos los puntos via spatial join
    df_total["comuna"] = asignar_comunas(df_total)

    return df_total


def asignar_comunas(df_input: pd.DataFrame, ruta_geojson: str = None) -> pd.Series:
    """
    Asigna comuna a cada punto via spatial join.
    Estrategia: within primero, nearest como fallback para cobertura 100%.
    """
    import geopandas as gpd
    from shapely.geometry import Point
    import os

    if ruta_geojson is None:
        ruta_geojson = os.path.join(os.path.dirname(__file__), "data", "comunas_santiago.geojson")

    if not os.path.exists(ruta_geojson):
        log.warning("GeoJSON de comunas no encontrado. Columna 'comuna' no asignada.")
        return pd.Series([None] * len(df_input), index=df_input.index)

    gdf_com = gpd.read_file(ruta_geojson).set_crs(epsg=4326).to_crs(epsg=32719)

    gdf_pts = gpd.GeoDataFrame(
        {"_pos": range(len(df_input))},
        geometry=gpd.points_from_xy(df_input["longitud"], df_input["latitud"]),
        crs="EPSG:4326"
    ).to_crs(epsg=32719)

    join = gpd.sjoin(gdf_pts, gdf_com[["comuna","geometry"]], how="left", predicate="within")
    join = join[~join.index.duplicated(keep="first")]
    comunas = join["comuna"].copy()

    sin_idx = comunas[comunas.isna()].index.tolist()
    if sin_idx:
        pts_sin = gdf_pts.loc[sin_idx]
        near = gpd.sjoin_nearest(pts_sin, gdf_com[["comuna","geometry"]], how="left")
        near = near[~near.index.duplicated(keep="first")]
        comunas.loc[sin_idx] = near["comuna"].values

    result = pd.Series(comunas.values, index=df_input.index)
    log.info(f"Comunas asignadas: {result.notna().sum()}/{len(result)} puntos")
    return result
