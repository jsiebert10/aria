PYTHON   := python3.12
VENV     := $(CURDIR)/.venv
BIN      := $(VENV)/bin
APP_DIR  := $(CURDIR)/codes_nahita/pages
DATA_DIR := $(APP_DIR)/data

.PHONY: venv install data geodata synthdata run clean

## Create virtualenv
venv:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

## Install dependencies into venv
install: venv
	$(BIN)/pip install -r $(APP_DIR)/requirements.txt

## Download comuna boundaries + generate synthetic data
data: geodata synthdata

geodata: install
	mkdir -p $(DATA_DIR)
	cd $(APP_DIR) && $(BIN)/python descargar_comunas.py

synthdata: install
	mkdir -p $(DATA_DIR)
	cd $(APP_DIR) && $(BIN)/python generar_sinteticos_v2.py

## Run the dashboard
run: install
	cd $(APP_DIR) && $(BIN)/python app.py

## Remove venv and generated data
clean:
	rm -rf $(VENV)
	rm -rf $(DATA_DIR)/*.xlsx $(DATA_DIR)/comunas_santiago.geojson
