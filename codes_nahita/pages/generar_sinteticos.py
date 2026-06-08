# =============================================================================
# generar_sinteticos.py — Generador de datos de prueba con drift mensual
# Las coordenadas usan un OFFSET deliberado para no coincidir con lugares reales.
# Guardar en data/ como archivos mensuales: enero_2025.xlsx, etc.
# =============================================================================

import os
import numpy as np
import pandas as pd
from config import RUTA_DATOS, TIPOS_PENALES_VALIDOS, MESES_ES

# ── Parámetros configurables ──────────────────────────────────────────────────
N_HECHOS_POR_MES   = 60      # Registros por archivo mensual
N_MESES            = 6       # Cuántos meses generar
MES_INICIO         = 1       # Mes de inicio (1 = enero)
ANIO_INICIO        = 2025
DRIFT_GRADOS_MES   = 0.008   # Desplazamiento del cluster por mes (en grados)
N_CLUSTERS         = 3       # Número de focos de concentración

# OFFSET ficticio: desplaza coordenadas para que NO correspondan a ningún lugar real.
# Poner en 0.0 para generar datos en coordenadas reales de prueba.
OFFSET_LAT = 0.0
OFFSET_LON = 0.0

# Semillas de clusters ficticios (se suman los offsets antes de guardar)
CLUSTERS_BASE = [
    {"lat": -33.45, "lon": -70.65, "peso": 0.45},
    {"lat": -33.52, "lon": -70.58, "peso": 0.35},
    {"lat": -33.40, "lon": -70.70, "peso": 0.20},
]

SEED = 42

# ── Lógica de generación ──────────────────────────────────────────────────────

def generar_mes(mes_idx: int, rng: np.random.Generator) -> pd.DataFrame:
    """
    Genera registros para un mes dado.
    mes_idx: 0 = primer mes, 1 = segundo mes, etc.
    El drift se acumula mes a mes en dirección noreste.
    """
    tipos_validos = [t for t in TIPOS_PENALES_VALIDOS if t != "Otro"]
    registros = []

    # Drift acumulado por mes (mueve los clusters progresivamente)
    drift_lat =  mes_idx * DRIFT_GRADOS_MES
    drift_lon =  mes_idx * DRIFT_GRADOS_MES * 0.6

    pesos = [c["peso"] for c in CLUSTERS_BASE]

    for _ in range(N_HECHOS_POR_MES):
        # Seleccionar cluster según pesos
        idx_cluster = rng.choice(len(CLUSTERS_BASE), p=pesos)
        base = CLUSTERS_BASE[idx_cluster]

        # Coordenadas con dispersión gaussiana + drift mensual + OFFSET ficticio
        lat = base["lat"] + drift_lat + rng.normal(0, 0.012) + OFFSET_LAT
        lon = base["lon"] + drift_lon + rng.normal(0, 0.012) + OFFSET_LON

        fenomeno = rng.choice(tipos_validos)

        registros.append({
            "fenomeno": fenomeno,
            "latitud":  round(lat, 6),
            "longitud": round(lon, 6),
        })

    return pd.DataFrame(registros)


def nombre_mes_archivo(mes_num: int, anio: int) -> str:
    """Retorna el nombre de archivo esperado: enero_2025.xlsx"""
    mes_nombre = {v: k for k, v in MESES_ES.items()}[mes_num]
    return f"{mes_nombre}_{anio}.xlsx"


def generar_todos(
    n_meses: int = N_MESES,
    n_hechos: int = N_HECHOS_POR_MES,
    mes_inicio: int = MES_INICIO,
    anio_inicio: int = ANIO_INICIO,
    ruta_salida: str = RUTA_DATOS,
):
    """
    Genera N_MESES archivos Excel en la carpeta de datos.
    Cada archivo tiene el formato: mes_año.xlsx
    """
    os.makedirs(ruta_salida, exist_ok=True)
    rng = np.random.default_rng(SEED)

    mes_actual = mes_inicio
    anio_actual = anio_inicio

    for i in range(n_meses):
        df = generar_mes(mes_idx=i, rng=rng)

        # Ajustar n_hechos si se configuró diferente
        if n_hechos != N_HECHOS_POR_MES:
            df = df.sample(n=min(n_hechos, len(df)), random_state=SEED)

        nombre = nombre_mes_archivo(mes_actual, anio_actual)
        ruta   = os.path.join(ruta_salida, nombre)
        df.to_excel(ruta, index=False)
        print(f"  ✓ {nombre} ({len(df)} registros)")

        # Avanzar al siguiente mes
        mes_actual += 1
        if mes_actual > 12:
            mes_actual = 1
            anio_actual += 1

    print(f"\nDatos sintéticos generados en: {ruta_salida}")
    print(f"NOTA: Coordenadas ficticias con offset lat+{OFFSET_LAT}, lon+{OFFSET_LON}")
    print(f"      No corresponden a ningún lugar real.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generador de datos sintéticos de prueba")
    parser.add_argument("--meses",   type=int, default=N_MESES,           help="Número de meses a generar")
    parser.add_argument("--hechos",  type=int, default=N_HECHOS_POR_MES,  help="Hechos por mes")
    parser.add_argument("--inicio",  type=int, default=MES_INICIO,        help="Mes de inicio (1-12)")
    parser.add_argument("--anio",    type=int, default=ANIO_INICIO,       help="Año de inicio")
    args = parser.parse_args()

    print(f"Generando {args.meses} meses de datos sintéticos ({args.hechos} hechos/mes)...")
    generar_todos(
        n_meses=args.meses,
        n_hechos=args.hechos,
        mes_inicio=args.inicio,
        anio_inicio=args.anio,
    )
