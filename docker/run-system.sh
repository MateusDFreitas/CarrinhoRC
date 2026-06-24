#!/usr/bin/env bash
set -e

CAMERA_INDEX="${CAMERA_INDEX:-0}"
CAMERA_FPS="${CAMERA_FPS:-20.0}"
ENABLE_CAMERA="${ENABLE_CAMERA:-true}"
ENABLE_ROSBRIDGE="${ENABLE_ROSBRIDGE:-true}"
MAX_LINEAR_SPEED="${MAX_LINEAR_SPEED:-1.0}"
MAX_ANGULAR_SPEED="${MAX_ANGULAR_SPEED:-1.0}"
DASHBOARD_HOST="${DASHBOARD_HOST:-0.0.0.0}"
DASHBOARD_PORT="${DASHBOARD_PORT:-5173}"
ROSBRIDGE_URL="${ROSBRIDGE_URL:-ws://localhost:9090}"
ROSBRIDGE_PORT="${ROSBRIDGE_PORT:-9090}"
ROS_LOG_DIR="${ROS_LOG_DIR:-/workspace/log/ros}"

mkdir -p "${ROS_LOG_DIR}"
export ROS_LOG_DIR
export VITE_ROSBRIDGE_URL="${ROSBRIDGE_URL}"

echo "Iniciando ROS2..."
ros2 launch rover_bringup rover.launch.py \
  camera_index:="${CAMERA_INDEX}" \
  camera_fps:="${CAMERA_FPS}" \
  enable_camera:="${ENABLE_CAMERA}" \
  enable_rosbridge:="${ENABLE_ROSBRIDGE}" \
  rosbridge_port:="${ROSBRIDGE_PORT}" \
  max_linear_speed:="${MAX_LINEAR_SPEED}" \
  max_angular_speed:="${MAX_ANGULAR_SPEED}" &
ROS_PID=$!

cleanup() {
  echo "Encerrando..."
  kill "${ROS_PID}" 2>/dev/null || true
  wait "${ROS_PID}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Iniciando dashboard em http://localhost:${DASHBOARD_PORT}"
npm run dev --prefix /workspace/dashboard -- --host "${DASHBOARD_HOST}" --port "${DASHBOARD_PORT}"
