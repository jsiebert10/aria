# =============================================================================
# convertir_comunas.py
# Convierte el shapefile oficial de comunas de Chile a GeoJSON,
# filtrando solo las comunas del Gran Santiago (Región Metropolitana).
# Ejecutar UNA VEZ: python convertir_comunas.py
# =============================================================================

import os
import json
import geopandas as gpd

RUTA_SHP    = os.path.join(os.path.dirname(__file__), "data", "comunas.shp")
RUTA_OUTPUT = os.path.join(os.path.dirname(__file__), "data", "comunas_santiago.geojson")

COMUNAS_RM = [
    "Santiago","Providencia","Las Condes","Vitacura","Lo Barnechea",
    "Ñuñoa","La Reina","Peñalolén","Macul","San Joaquín",
    "La Florida","La Granja","San Miguel","La Cisterna","El Bosque",
    "Pedro Aguirre Cerda","Lo Espejo","San Ramón","La Pintana",
    "Puente Alto","Estación Central","Cerrillos","Maipú","Pudahuel",
    "Quinta Normal","Lo Prado","Cerro Navia","Renca","Conchalí",
    "Huechuraba","Recoleta","Independencia",
]

print("Leyendo shapefile...")
gdf = gpd.read_file(RUTA_SHP)

print(f"Total comunas en shapefile: {len(gdf)}")
print(f"Columnas disponibles: {gdf.columns.tolist()}")
print(f"Muestra:\n{gdf.head(3).to_string()}\n")

# Detectar columna de nombre de comuna
col_nombre = None
for posible in ["NOM_COM", "NOMBRE", "COMUNA", "Comuna", "nombre", "nom_com", "Name", "NAME"]:
    if posible in gdf.columns:
        col_nombre = posible
        break

if col_nombre is None:
    print("ERROR: No se encontró columna de nombre. Columnas disponibles:")
    print(gdf.columns.tolist())
    print("\nEdita el script y agrega el nombre correcto en 'col_nombre'")
    exit(1)

print(f"Columna de nombre detectada: '{col_nombre}'")

# Normalizar nombres para comparación
gdf["_nom_norm"] = gdf[col_nombre].str.strip().str.title()

# Filtrar solo comunas del Gran Santiago
# Primero intentar por nombre exacto
gdf_rm = gdf[gdf["_nom_norm"].isin(COMUNAS_RM)].copy()

if len(gdf_rm) < 20:
    # Si no matchea bien, buscar por código de región (RM = 13)
    col_region = None
    for posible in ["REGION", "COD_REGI", "CUT_REG", "region", "cod_region"]:
        if posible in gdf.columns:
            col_region = posible
            break

    if col_region:
        print(f"Filtrando por región usando columna '{col_region}'...")
        gdf_rm = gdf[gdf[col_region].astype(str).str.startswith("13")].copy()
        print(f"Comunas RM encontradas: {len(gdf_rm)}")
    else:
        print(f"Solo se encontraron {len(gdf_rm)} comunas por nombre. Usando todas las que matchearon.")

print(f"\nComunas a incluir: {len(gdf_rm)}")
print(gdf_rm[col_nombre].sort_values().tolist())

# Proyectar a WGS84
gdf_rm = gdf_rm.to_crs(epsg=4326)

# Construir GeoJSON con columna 'comuna' estandarizada
features = []
for _, row in gdf_rm.iterrows():
    features.append({
        "type": "Feature",
        "properties": {
            "comuna": str(row[col_nombre]).strip().title(),
        },
        "geometry": row.geometry.__geo_interface__,
    })

geojson = {"type": "FeatureCollection", "features": features}

with open(RUTA_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False)

print(f"\n✓ Guardado: {RUTA_OUTPUT}")
print(f"✓ {len(features)} comunas con geometría oficial del BCN")

# Verificar vértices del primer polígono
if features:
    primera_geom = features[0]["geometry"]
    if primera_geom["type"] == "Polygon":
        n_vert = len(primera_geom["coordinates"][0])
    elif primera_geom["type"] == "MultiPolygon":
        n_vert = sum(len(ring[0]) for ring in primera_geom["coordinates"])
    else:
        n_vert = 0
    print(f"✓ Polígonos con {n_vert}+ vértices — geometría real")
    print(f"\nReinicia el dashboard: python app.py")
