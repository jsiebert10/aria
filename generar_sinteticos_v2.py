# =============================================================================
# generar_sinteticos_v2.py — ARIA v3
# Genera datos sintéticos robustos:
#   · 12 meses (enero–diciembre 2025)
#   · ~100 hechos por comuna activa por mes
#   · Columnas: fenomeno, fecha, hora, latitud, longitud
#   · Patrones criminológicos realistas (horarios, concentración comunal)
# Ejecutar: python generar_sinteticos_v2.py
# =============================================================================

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

RUTA = os.path.join(os.path.dirname(__file__), "data")

MESES = [
    ("enero",      1),  ("febrero",   2),  ("marzo",     3),
    ("abril",      4),  ("mayo",      5),  ("junio",     6),
    ("julio",      7),  ("agosto",    8),  ("septiembre",9),
    ("octubre",   10),  ("noviembre",11),  ("diciembre", 12),
]

FENOMENOS = [
    "Robo con violencia",
    "Robo en casa",
    "Hurto",
    "Daños",
    "Robo a vehículo",
    "Robo en comercio",
    "Lesiones",
    "Receptación",
]

# Comunas Gran Santiago con coordenadas centrales y radio de dispersión
COMUNAS = [
    {"nombre":"Santiago",          "lat":-33.457, "lon":-70.648, "radio":0.025, "peso":1.8},
    {"nombre":"Providencia",       "lat":-33.433, "lon":-70.611, "radio":0.018, "peso":1.5},
    {"nombre":"Las Condes",        "lat":-33.410, "lon":-70.570, "radio":0.030, "peso":1.3},
    {"nombre":"Ñuñoa",             "lat":-33.456, "lon":-70.598, "radio":0.018, "peso":1.2},
    {"nombre":"Maipú",             "lat":-33.520, "lon":-70.760, "radio":0.035, "peso":1.4},
    {"nombre":"La Florida",        "lat":-33.520, "lon":-70.570, "radio":0.030, "peso":1.3},
    {"nombre":"Puente Alto",       "lat":-33.610, "lon":-70.570, "radio":0.035, "peso":1.2},
    {"nombre":"Recoleta",          "lat":-33.405, "lon":-70.650, "radio":0.020, "peso":1.3},
    {"nombre":"Independencia",     "lat":-33.420, "lon":-70.670, "radio":0.015, "peso":1.1},
    {"nombre":"Estación Central",  "lat":-33.470, "lon":-70.695, "radio":0.018, "peso":1.1},
    {"nombre":"Macul",             "lat":-33.490, "lon":-70.595, "radio":0.018, "peso":1.0},
    {"nombre":"San Joaquín",       "lat":-33.490, "lon":-70.625, "radio":0.015, "peso":1.0},
    {"nombre":"La Granja",         "lat":-33.520, "lon":-70.620, "radio":0.018, "peso":1.0},
    {"nombre":"San Miguel",        "lat":-33.500, "lon":-70.655, "radio":0.018, "peso":1.1},
    {"nombre":"Peñalolén",         "lat":-33.490, "lon":-70.540, "radio":0.030, "peso":1.1},
    {"nombre":"Vitacura",          "lat":-33.380, "lon":-70.590, "radio":0.022, "peso":0.8},
    {"nombre":"Lo Barnechea",      "lat":-33.350, "lon":-70.520, "radio":0.040, "peso":0.7},
    {"nombre":"Conchalí",          "lat":-33.395, "lon":-70.680, "radio":0.018, "peso":1.0},
    {"nombre":"Huechuraba",        "lat":-33.365, "lon":-70.650, "radio":0.025, "peso":0.9},
    {"nombre":"Pudahuel",          "lat":-33.430, "lon":-70.760, "radio":0.040, "peso":1.1},
    {"nombre":"Cerrillos",         "lat":-33.500, "lon":-70.720, "radio":0.020, "peso":0.9},
    {"nombre":"Quinta Normal",     "lat":-33.440, "lon":-70.710, "radio":0.015, "peso":1.0},
    {"nombre":"Lo Prado",          "lat":-33.460, "lon":-70.710, "radio":0.015, "peso":1.0},
    {"nombre":"Cerro Navia",       "lat":-33.440, "lon":-70.735, "radio":0.018, "peso":1.1},
    {"nombre":"Renca",             "lat":-33.405, "lon":-70.710, "radio":0.020, "peso":1.0},
    {"nombre":"Pedro Aguirre Cerda","lat":-33.500,"lon":-70.685, "radio":0.015, "peso":1.0},
    {"nombre":"Lo Espejo",         "lat":-33.525, "lon":-70.690, "radio":0.018, "peso":1.0},
    {"nombre":"San Ramón",         "lat":-33.540, "lon":-70.620, "radio":0.015, "peso":0.9},
    {"nombre":"La Pintana",        "lat":-33.580, "lon":-70.640, "radio":0.030, "peso":1.1},
    {"nombre":"La Cisterna",       "lat":-33.525, "lon":-70.655, "radio":0.015, "peso":0.9},
    {"nombre":"El Bosque",         "lat":-33.550, "lon":-70.655, "radio":0.018, "peso":1.0},
    {"nombre":"La Reina",          "lat":-33.448, "lon":-70.550, "radio":0.025, "peso":0.9},
]

# Distribución horaria realista (patrón criminológico RM)
PROB_HORA = np.array([
    0.012, 0.008, 0.006, 0.004, 0.003, 0.003,  # 00-05
    0.008, 0.018, 0.030, 0.040, 0.048, 0.052,  # 06-11
    0.055, 0.058, 0.055, 0.052, 0.050, 0.060,  # 12-17
    0.070, 0.075, 0.072, 0.065, 0.050, 0.028,  # 18-23
])
PROB_HORA = PROB_HORA / PROB_HORA.sum()

# Mix por fenómeno (distribución relativa)
PESO_FEN = {
    "Robo con violencia": 0.18,
    "Hurto":              0.22,
    "Robo en casa":       0.14,
    "Robo a vehículo":    0.16,
    "Robo en comercio":   0.12,
    "Daños":              0.08,
    "Lesiones":           0.06,
    "Receptación":        0.04,
}

# Drift espacial mensual (simula movilidad real del fenómeno)
DRIFT = {
    "Robo con violencia": (0.001,  0.0005),
    "Hurto":              (-0.0005, 0.001),
    "Robo en casa":       (0.0008, -0.0003),
    "Robo a vehículo":    (-0.0003, 0.0008),
    "Robo en comercio":   (0.0005,  0.0005),
    "Daños":              (0.0002, -0.0002),
    "Lesiones":           (-0.0002, 0.0003),
    "Receptación":        (0.0003,  0.0003),
}

print("=" * 55)
print("  Generando datos sintéticos ARIA v3")
print("  12 meses · fecha · hora · ~100 hechos/comuna")
print("=" * 55)

total_generado = 0

for nombre_mes, num_mes in MESES:
    registros = []
    anio = 2025

    # Días del mes
    if num_mes in [1,3,5,7,8,10,12]:
        dias = 31
    elif num_mes == 2:
        dias = 28
    else:
        dias = 30

    for com in COMUNAS:
        # Hechos por comuna: entre 80 y 140, modulado por peso
        n_base = int(np.random.normal(110 * com["peso"], 15))
        n_base = max(80, min(160, n_base))

        for fen, peso_fen in PESO_FEN.items():
            n_fen = max(5, int(n_base * peso_fen * np.random.uniform(0.85, 1.15)))

            # Drift acumulado
            drift_lat, drift_lon = DRIFT[fen]
            offset_lat = drift_lat * (num_mes - 1)
            offset_lon = drift_lon * (num_mes - 1)

            for _ in range(n_fen):
                # Coordenadas con dispersión gaussiana
                lat = com["lat"] + offset_lat + np.random.normal(0, com["radio"] * 0.4)
                lon = com["lon"] + offset_lon + np.random.normal(0, com["radio"] * 0.4)

                # Fecha aleatoria dentro del mes
                dia = np.random.randint(1, dias + 1)
                fecha = f"{anio:04d}-{num_mes:02d}-{dia:02d}"

                # Hora según distribución aorística
                hora_int = np.random.choice(24, p=PROB_HORA)
                minuto   = np.random.randint(0, 60)
                hora_str = f"{hora_int:02d}:{minuto:02d}"

                registros.append({
                    "fenomeno": fen,
                    "fecha":    fecha,
                    "hora":     hora_str,
                    "latitud":  round(lat, 5),
                    "longitud": round(lon, 5),
                })

    df = pd.DataFrame(registros)

    # Nombre de archivo: mes_año.xlsx
    nombre_archivo = f"{nombre_mes}_{anio}.xlsx"
    ruta_salida = os.path.join(RUTA, nombre_archivo)

    df.to_excel(ruta_salida, index=False)
    total_generado += len(df)
    print(f"  ✓ {nombre_archivo}: {len(df):,} registros")

print(f"\n✓ Total generado: {total_generado:,} registros en 12 archivos")
print(f"✓ Guardado en: {RUTA}")
print("\nReinicia el dashboard: python app.py")
