#!/bin/sh

if [ ! -f data/comunas_santiago.geojson ]; then
    echo "Descargando comunas..."
    python scripts/descargar_comunas.py
fi

if [ ! -f data/enero_2025.xlsx ]; then
    echo "Generando datos sintéticos..."
    python scripts/generar_sinteticos_v2.py
fi

echo "Iniciando ARIA..."
exec python app.py
