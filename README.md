# ARIA

Plataforma de inteligencia criminal para la Región Metropolitana de Santiago, Chile. Dashboard interactivo construido con Dash (Flask) que corre 100% local.

## Inicio rápido

### Mac / Linux

**Con Docker:**

```bash
# Prerrequisitos (una sola vez)
brew install colima docker docker-compose   # Mac
# sudo apt install docker.io docker-compose  # Ubuntu/Debian

# Levantar
make docker       # inicia Colima (Mac) + construye imagen + arranca ARIA

# Cuando termines
make docker-down  # apaga contenedor + Colima
```

**Sin Docker (nativo):**

Requiere Python 3.12.

```bash
make data    # descarga GeoJSON + genera datos sintéticos (una sola vez)
make run     # inicia dashboard
```

### Windows

Requiere [Docker Desktop](https://docs.docker.com/desktop/install/windows-install/) (una sola vez).

```powershell
git clone https://github.com/jsiebert10/aria.git
cd aria
docker-compose up --build

# Cuando termines
docker-compose down
```

---

En todos los casos la app genera los datos automáticamente si no existen y queda disponible en **http://localhost:8050**.

## Claude API (opcional)

Los módulos de agrupación de casos y policy brief usan la API de Claude. Para activarlos, crea un archivo `.env` en la raíz del proyecto:

```
ANTHROPIC_API_KEY=tu_clave_aquí
```

Sin este archivo la app funciona normalmente, solo esos dos módulos quedan deshabilitados.
