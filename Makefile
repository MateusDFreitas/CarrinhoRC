SHELL := /bin/bash

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
DASHBOARD_DIR := dashboard
SERIAL_PORT ?= /dev/ttyUSB0
BAUD_RATE ?= 115200
DASHBOARD_HOST ?= 0.0.0.0
DASHBOARD_PORT ?= 8000
DOCKER_IMAGE ?= carrinhorc:python
COMPOSE ?= docker compose

.PHONY: help deps deps-python deps-dashboard doctor build-dashboard run run-serial dashboard run-dashboard docker-build docker-run docker-down clean

help:
	@echo "CarrinhoRC targets:"
	@echo "  make deps        instala dependencias Python"
	@echo "  make build-dashboard compila a dashboard React"
	@echo "  make doctor      verifica Python, pyserial e porta USB"
	@echo "  make run         abre dashboard web para controle USB"
	@echo "  make dashboard   alias de make run"
	@echo "  make run-serial  roda controle manual no terminal"
	@echo "  make docker-build constroi imagem Docker"
	@echo "  make docker-run   roda dashboard pelo Docker"
	@echo "  make docker-down  encerra Docker Compose"
	@echo "  make clean       remove caches Python"
	@echo ""
	@echo "Variaveis uteis:"
	@echo "  PYTHON=$(PYTHON)"
	@echo "  SERIAL_PORT=$(SERIAL_PORT)"
	@echo "  BAUD_RATE=$(BAUD_RATE)"
	@echo "  DASHBOARD_PORT=$(DASHBOARD_PORT)"

deps: deps-python deps-dashboard

deps-python:
	$(PIP) install -r requirements.txt

deps-dashboard:
	npm install --prefix $(DASHBOARD_DIR)

doctor:
	@echo "== Python =="
	@$(PYTHON) --version
	@echo ""
	@echo "== pyserial =="
	@$(PYTHON) -c 'import serial; print("OK: pyserial", serial.VERSION)' 2>/dev/null || echo "FALTANDO: make deps"
	@echo ""
	@echo "== Portas seriais =="
	@if ls /dev/ttyUSB* /dev/ttyACM* >/dev/null 2>&1; then ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; else echo "Nenhuma /dev/ttyUSB* ou /dev/ttyACM* encontrada"; fi
	@echo ""
	@if test -e "$(SERIAL_PORT)"; then echo "OK: $(SERIAL_PORT) existe"; else echo "AVISO: $(SERIAL_PORT) nao existe"; fi

build-dashboard: deps-dashboard
	npm run build --prefix $(DASHBOARD_DIR)

run dashboard run-dashboard: build-dashboard
	$(PYTHON) backend/server.py --port "$(SERIAL_PORT)" --baud "$(BAUD_RATE)" --host "$(DASHBOARD_HOST)" --http-port "$(DASHBOARD_PORT)"

run-serial:
	$(PYTHON) tools/servoandesc.py --port "$(SERIAL_PORT)" --baud "$(BAUD_RATE)"

docker-build:
	docker build -t "$(DOCKER_IMAGE)" .

docker-run:
	SERIAL_PORT="$(SERIAL_PORT)" \
	BAUD_RATE="$(BAUD_RATE)" \
	DASHBOARD_PORT="$(DASHBOARD_PORT)" \
	DOCKER_IMAGE="$(DOCKER_IMAGE)" \
	$(COMPOSE) up --build

docker-down:
	$(COMPOSE) down

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf $(DASHBOARD_DIR)/dist
