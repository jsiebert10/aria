# =============================================================================
# descargar_comunas.py
# Descarga los límites comunales reales del Gran Santiago desde OpenStreetMap.
# Ejecutar UNA SOLA VEZ con internet. Genera data/comunas_santiago.geojson
#
# Uso: python descargar_comunas.py
# Requiere: pip install osmnx
# =============================================================================

import os, sys, json

RUTA_SALIDA = os.path.join(os.path.dirname(__file__), "data", "comunas_santiago.geojson")

COMUNAS_RM = [
    "Santiago", "Providencia", "Las Condes", "Vitacura", "Lo Barnechea",
    "Ñuñoa", "La Reina", "Peñalolén", "Macul", "San Joaquín",
    "La Florida", "La Granja", "San Miguel", "La Cisterna", "El Bosque",
    "Pedro Aguirre Cerda", "Lo Espejo", "San Ramón", "La Pintana",
    "Puente Alto", "Estación Central", "Cerrillos", "Maipú", "Pudahuel",
    "Quinta Normal", "Lo Prado", "Cerro Navia", "Renca", "Conchalí",
    "Huechuraba", "Recoleta", "Independencia",
]

def descargar_con_osmnx():
    """Método 1: usar osmnx (más preciso)."""
    try:
        import osmnx as ox
        print("Usando osmnx...")
        features = []
        for i, comuna in enumerate(COMUNAS_RM):
            print(f"  [{i+1}/{len(COMUNAS_RM)}] {comuna}...", end=" ", flush=True)
            try:
                gdf = ox.geocode_to_gdf(f"{comuna}, Región Metropolitana, Chile")
                gdf = gdf.to_crs(epsg=4326)
                geom = gdf.geometry.iloc[0]
                features.append({
                    "type": "Feature",
                    "properties": {"comuna": comuna},
                    "geometry": geom.__geo_interface__,
                })
                print("OK")
            except Exception as e:
                print(f"Error: {e}")
        return features
    except ImportError:
        return None

def descargar_con_nominatim():
    """Método 2: usar Nominatim directamente (no requiere osmnx)."""
    import urllib.request, urllib.parse, time

    print("Usando Nominatim (OpenStreetMap)...")
    features = []

    for i, comuna in enumerate(COMUNAS_RM):
        print(f"  [{i+1}/{len(COMUNAS_RM)}] {comuna}...", end=" ", flush=True)
        try:
            query = urllib.parse.urlencode({
                "q": f"{comuna}, Región Metropolitana, Chile",
                "format": "geojson",
                "polygon_geojson": 1,
                "limit": 1,
                "addressdetails": 0,
            })
            url  = f"https://nominatim.openstreetmap.org/search?{query}"
            req  = urllib.request.Request(url, headers={
                "User-Agent": "ProyectoMovilidadDelictual/1.0"
            })
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())

            if data.get("features"):
                feat = data["features"][0]
                feat["properties"]["comuna"] = comuna
                features.append(feat)
                print("OK")
            else:
                print("Sin resultado")

            time.sleep(1.1)  # Nominatim pide max 1 req/seg

        except Exception as e:
            print(f"Error: {e}")

    return features

def descargar_con_overpass():
    """Método 3: Overpass API — más robusto para polígonos administrativos."""
    import urllib.request, urllib.parse, time

    print("Usando Overpass API...")
    features = []

    for i, comuna in enumerate(COMUNAS_RM):
        print(f"  [{i+1}/{len(COMUNAS_RM)}] {comuna}...", end=" ", flush=True)
        try:
            # Buscar relación administrativa de la comuna en Chile
            query = f"""
            [out:json][timeout:25];
            relation["name"="{comuna}"]["admin_level"="8"]["boundary"="administrative"];
            out geom;
            """
            url  = "https://overpass-api.de/api/interpreter"
            data = urllib.parse.urlencode({"data": query}).encode()
            req  = urllib.request.Request(url, data=data, headers={
                "User-Agent": "ProyectoMovilidadDelictual/1.0"
            })
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())

            elements = result.get("elements", [])
            if elements:
                el = elements[0]
                # Construir polígono desde members
                coords = []
                for member in el.get("members", []):
                    if member.get("type") == "way" and member.get("role") == "outer":
                        way_coords = [[n["lon"], n["lat"]] for n in member.get("geometry", [])]
                        coords.extend(way_coords)

                if coords:
                    features.append({
                        "type": "Feature",
                        "properties": {"comuna": comuna},
                        "geometry": {"type": "Polygon", "coordinates": [coords]},
                    })
                    print("OK")
                else:
                    print("Sin geometría")
            else:
                print("Sin resultado")

            time.sleep(0.5)

        except Exception as e:
            print(f"Error: {e}")

    return features


def guardar(features, ruta):
    geojson = {
        "type": "FeatureCollection",
        "features": [f for f in features if f],
    }
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"\n✓ Guardado: {ruta}")
    print(f"✓ {len(geojson['features'])} comunas con geometría real")


if __name__ == "__main__":
    print("=" * 55)
    print("  Descarga de límites comunales reales — Gran Santiago")
    print("=" * 55 + "\n")

    # Intentar métodos en orden de preferencia
    features = descargar_con_osmnx()

    if not features:
        features = descargar_con_nominatim()

    if not features:
        features = descargar_con_overpass()

    if features:
        guardar(features, RUTA_SALIDA)
        print("\nListo. Reinicia el dashboard: python app.py")
    else:
        print("\n✗ No se pudo descargar. Verifica tu conexión a internet.")
        sys.exit(1)
