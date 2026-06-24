PYTHON   := python3.12
VENV     := $(CURDIR)/.venv
BIN      := $(VENV)/bin
DATA_DIR := $(CURDIR)/data

.PHONY: venv install data geodata synthdata run clean docker docker-down

## Create virtualenv
venv:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

## Install dependencies into venv
install: venv
	$(BIN)/pip install -r requirements.txt

## Download comuna boundaries + generate synthetic data
data: geodata synthdata

geodata: install
	mkdir -p $(DATA_DIR)
	$(BIN)/python scripts/descargar_comunas.py

synthdata: install
	mkdir -p $(DATA_DIR)
	$(BIN)/python scripts/generar_sinteticos_v2.py

## Run the dashboard
run: install
	$(BIN)/python app.py

## Run with Docker (starts Colima if available)
docker:
	@colima status 2>/dev/null || colima start 2>/dev/null || true
	docker-compose up --build

## Stop Docker containers and Colima (if running)
docker-down:
	docker-compose down
	@colima status 2>/dev/null && colima stop || true

## Remove venv and generated data
clean:
	rm -rf $(VENV)
	rm -rf $(DATA_DIR)/*.xlsx $(DATA_DIR)/comunas_santiago.geojson
