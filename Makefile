SHELL := /bin/bash

ROS_DISTRO ?= humble
ROS_SETUP ?= /opt/ros/$(ROS_DISTRO)/setup.bash
ROS_LOG_DIR ?= $(CURDIR)/log/ros

DASHBOARD_DIR := dashboard
DASHBOARD_HOST ?= 0.0.0.0
DASHBOARD_PORT ?= 5173
ROSBRIDGE_URL ?= ws://localhost:9090
ROSBRIDGE_PORT ?= 9090

CAMERA_INDEX ?= 0
CAMERA_SOURCE ?=
CAMERA_FPS ?= 60.0
ENABLE_CAMERA ?= true
ENABLE_ROSBRIDGE ?= true
MAX_LINEAR_SPEED ?= 1.0
MAX_ANGULAR_SPEED ?= 1.0

DOCKER_IMAGE ?= carrinhorc:humble
COMPOSE ?= docker compose

.PHONY: help deps doctor build build-ros build-dashboard run run-ros run-dashboard docker-build docker-run docker-down clean clean-dashboard clean-ros

help:
	@echo "CarrinhoRC targets:"
	@echo "  make deps              instala dependencias npm da dashboard"
	@echo "  make doctor            verifica ROS, rosbridge e webcams"
	@echo "  make build             compila ROS2 e dashboard"
	@echo "  make run               roda ROS2 + dashboard no mesmo terminal"
	@echo "  make run-ros           roda somente o launch ROS2"
	@echo "  make run-dashboard     roda somente a dashboard"
	@echo "  make docker-build      constroi a imagem Docker"
	@echo "  make docker-run        roda o sistema pelo Docker Compose"
	@echo "  make docker-down       encerra o Compose"
	@echo "  make clean             remove build/install/log/dist"
	@echo ""
	@echo "Variaveis uteis:"
	@echo "  ROS_DISTRO=$(ROS_DISTRO)"
	@echo "  CAMERA_INDEX=$(CAMERA_INDEX)"
	@echo "  CAMERA_SOURCE=$(CAMERA_SOURCE)"
	@echo "  ENABLE_CAMERA=$(ENABLE_CAMERA)"
	@echo "  ENABLE_ROSBRIDGE=$(ENABLE_ROSBRIDGE)"
	@echo "  DASHBOARD_PORT=$(DASHBOARD_PORT)"
	@echo "  ROSBRIDGE_URL=$(ROSBRIDGE_URL)"
	@echo "  ROSBRIDGE_PORT=$(ROSBRIDGE_PORT)"
	@echo "  DOCKER_IMAGE=$(DOCKER_IMAGE)"

deps:
	npm install --prefix $(DASHBOARD_DIR)

doctor:
	@echo "== ROS =="
	@if test -f "$(ROS_SETUP)"; then echo "OK: $(ROS_SETUP)"; else echo "ERRO: $(ROS_SETUP) nao encontrado"; fi
	@bash -lc 'source "$(ROS_SETUP)" 2>/dev/null && ros2 --version 2>/dev/null || true'
	@echo ""
	@echo "== rosbridge_server =="
	@bash -lc 'source "$(ROS_SETUP)" 2>/dev/null && ros2 pkg prefix rosbridge_server >/dev/null 2>&1 && echo "OK: rosbridge_server instalado" || echo "FALTANDO: sudo apt install ros-\$$ROS_DISTRO-rosbridge-server"'
	@echo ""
	@echo "== OpenCV Python =="
	@python3 -c 'import cv2; print("OK: cv2", cv2.__version__)' 2>/dev/null || echo "FALTANDO: sudo apt install python3-opencv"
	@echo ""
	@echo "== Dispositivos de video =="
	@if ls /dev/video* >/dev/null 2>&1; then ls -l /dev/video*; else echo "Nenhum /dev/video* encontrado"; fi

build: build-ros build-dashboard

build-ros:
	@test -f "$(ROS_SETUP)" || (echo "ROS setup nao encontrado: $(ROS_SETUP)" && exit 1)
	source "$(ROS_SETUP)" && colcon build

build-dashboard: deps
	npm run build --prefix $(DASHBOARD_DIR)

run: build-ros deps
	@test -f "$(ROS_SETUP)" || (echo "ROS setup nao encontrado: $(ROS_SETUP)" && exit 1)
	@mkdir -p "$(ROS_LOG_DIR)"
	@set -eo pipefail; \
	source "$(ROS_SETUP)"; \
	source install/setup.bash; \
	export ROS_LOG_DIR="$(ROS_LOG_DIR)"; \
	export VITE_ROSBRIDGE_URL="$(ROSBRIDGE_URL)"; \
	echo "Iniciando ROS2..."; \
		ros2 launch rover_bringup rover.launch.py \
		camera_index:=$(CAMERA_INDEX) \
		camera_source:="$(CAMERA_SOURCE)" \
		camera_fps:=$(CAMERA_FPS) \
		enable_camera:=$(ENABLE_CAMERA) \
		enable_rosbridge:=$(ENABLE_ROSBRIDGE) \
		rosbridge_port:=$(ROSBRIDGE_PORT) \
		max_linear_speed:=$(MAX_LINEAR_SPEED) \
		max_angular_speed:=$(MAX_ANGULAR_SPEED) & \
	ROS_PID=$$!; \
	trap 'echo "Encerrando..."; kill $$ROS_PID 2>/dev/null || true; wait $$ROS_PID 2>/dev/null || true' INT TERM EXIT; \
	echo "Iniciando dashboard em http://localhost:$(DASHBOARD_PORT)"; \
	npm run dev --prefix "$(DASHBOARD_DIR)" -- --host "$(DASHBOARD_HOST)" --port "$(DASHBOARD_PORT)"

run-ros: build-ros
	@mkdir -p "$(ROS_LOG_DIR)"
	source "$(ROS_SETUP)" && \
	source install/setup.bash && \
	ROS_LOG_DIR="$(ROS_LOG_DIR)" ros2 launch rover_bringup rover.launch.py \
		camera_index:=$(CAMERA_INDEX) \
		camera_source:="$(CAMERA_SOURCE)" \
		camera_fps:=$(CAMERA_FPS) \
		enable_camera:=$(ENABLE_CAMERA) \
		enable_rosbridge:=$(ENABLE_ROSBRIDGE) \
		rosbridge_port:=$(ROSBRIDGE_PORT) \
		max_linear_speed:=$(MAX_LINEAR_SPEED) \
		max_angular_speed:=$(MAX_ANGULAR_SPEED)

run-dashboard: deps
	VITE_ROSBRIDGE_URL="$(ROSBRIDGE_URL)" npm run dev --prefix "$(DASHBOARD_DIR)" -- --host "$(DASHBOARD_HOST)" --port "$(DASHBOARD_PORT)"

docker-build:
	docker build -t "$(DOCKER_IMAGE)" .

docker-run:
	CAMERA_INDEX="$(CAMERA_INDEX)" \
	CAMERA_SOURCE="$(CAMERA_SOURCE)" \
	CAMERA_FPS="$(CAMERA_FPS)" \
	ENABLE_CAMERA="$(ENABLE_CAMERA)" \
	ENABLE_ROSBRIDGE="$(ENABLE_ROSBRIDGE)" \
	MAX_LINEAR_SPEED="$(MAX_LINEAR_SPEED)" \
	MAX_ANGULAR_SPEED="$(MAX_ANGULAR_SPEED)" \
	DASHBOARD_HOST="$(DASHBOARD_HOST)" \
	DASHBOARD_PORT="$(DASHBOARD_PORT)" \
	ROSBRIDGE_URL="$(ROSBRIDGE_URL)" \
	ROSBRIDGE_PORT="$(ROSBRIDGE_PORT)" \
	$(COMPOSE) up --build

docker-down:
	$(COMPOSE) down

clean: clean-ros clean-dashboard

clean-ros:
	rm -rf build install log

clean-dashboard:
	rm -rf $(DASHBOARD_DIR)/dist
