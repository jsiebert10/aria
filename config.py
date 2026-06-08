# =============================================================================
# config.py — Parámetros centralizados del sistema de movilidad delictual
# Modificar aquí para adaptar el sistema sin tocar otros módulos.
# =============================================================================

import os

# ── Rutas ─────────────────────────────────────────────────────────────────────
# Carpeta donde se depositan los archivos mensuales (formato: mes_año.xlsx)
RUTA_DATOS = os.path.join(os.path.dirname(__file__), "data")

# ── Sistema de coordenadas ────────────────────────────────────────────────────
EPSG_CALCULO = 32719   # Proyectado en metros — UTM zona 19S (Chile central)
EPSG_MAPA    = 4326    # WGS84 — para visualización en Leaflet

# ── Umbrales de cálculo ───────────────────────────────────────────────────────
MIN_PUNTOS_CALCULO = 5  # Mínimo de puntos para calcular métricas espaciales

# ── Centro y zoom inicial del mapa ───────────────────────────────────────────
CENTRO_MAPA_DEFAULT = (-33.45, -70.65)  # Santiago centro
ZOOM_DEFAULT        = 11

# ── Rango de coordenadas válidas ──────────────────────────────────────────────
# Chile continental por defecto. Ajustar si se trabaja con otra zona.
RANGO_LAT = (-56, -17)   # (sur, norte)
RANGO_LON = (-76, -66)   # (oeste, este)
# El módulo ingesta.py normaliza cualquier valor a esta lista.
# Agregar nuevas categorías aquí si el catálogo institucional cambia.
TIPOS_PENALES_VALIDOS = [
    "Robo a vehículo",
    "Robo en casa",
    "Robo con violencia",
    "Robo en comercio",
    "Hurto",
    "Daños",
    "Lesiones",
    "Receptación",
    "Receptación",
    "Asalto en la vía pública",
    "Otro",
]

# ── Mapeo de normalización (variantes → categoría canónica) ──────────────────
# Las claves son fragmentos que pueden aparecer en los datos crudos.
# Se aplica en orden: primero coincidencia exacta, luego búsqueda parcial.
MAPA_NORMALIZACION = {
    "robo a vehiculo":        "Robo a vehículo",
    "robo vehiculo":          "Robo a vehículo",
    "robo auto":              "Robo a vehículo",
    "robo casa":              "Robo en casa",
    "robo en casa":           "Robo en casa",
    "robo habitacion":        "Robo en casa",
    "robo con violencia":     "Robo con violencia",
    "robo con intimidacion":  "Robo con violencia",
    "robo comercio":          "Robo en comercio",
    "robo en comercio":       "Robo en comercio",
    "hurto":                  "Hurto",
    "danos":                  "Daños",
    "lesiones":               "Lesiones",
    "Lesiones":               "Lesiones",
    "receptacion":            "Receptación",
    "receptación":            "Receptación",
    "Receptación":            "Receptación",
    "daños":                  "Daños",
    "receptacion":            "Receptación",
    "receptación":            "Receptación",
    "asalto via publica":     "Asalto en la vía pública",
    "asalto en la via":       "Asalto en la vía pública",
    "asalto vía pública":     "Asalto en la vía pública",
}

# ── Formato de nombre de archivo ──────────────────────────────────────────────
# El sistema espera: mes_año.xlsx  (ej: enero_2025.xlsx)
# Meses válidos en español (minúsculas)
MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# ── Paleta de colores por tipo penal ─────────────────────────────────────────
COLORES_TIPOS = {
    "Robo a vehículo":          "#4f8ef7",
    "Robo en casa":             "#f75f5f",
    "Robo con violencia":       "#f7b84f",
    "Robo en comercio":         "#4fcc8e",
    "Hurto":                    "#7c5cfc",
    "Daños":                    "#f75fc8",
    "Lesiones":                 "#c74d3f",
    "Receptación":              "#5a8fa8",
    "Receptación":              "#5cf7e8",
    "Asalto en la vía pública": "#cc4fcc",
    "Otro":                     "#8b91b0",
}

# ── Colores de capas en el mapa ───────────────────────────────────────────────
COLOR_ELIPSE_ACTUAL   = "#4f8ef7"   # Azul — período seleccionado
COLOR_ELIPSE_ANTERIOR = "#f75f5f"   # Rojo — período anterior (comparación)
COLOR_TRAYECTORIA     = "#f7b84f"   # Ámbar — línea de trayectoria

# ── Clasificación de solapamiento ─────────────────────────────────────────────
UMBRAL_ESTABLE      = 0.70   # Jaccard >= 0.70 → patrón estable
UMBRAL_PARCIAL      = 0.30   # Jaccard 0.30–0.70 → desplazamiento parcial
                              # Jaccard < 0.30 → desplazamiento significativo
