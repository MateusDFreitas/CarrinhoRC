# CarrinhoRC

Sistema ROS2 + dashboard web para um carrinho com webcam, ESC e servo de direcao.

## Arquitetura

- `src/rover_control`: nos ROS2 em Python para controle manual, telemetria e camera.
- `src/rover_bringup`: launch principal do sistema.
- `dashboard`: interface React integrada ao ROS2 via `rosbridge_server`.

## Topicos principais

- `/cmd_vel` (`geometry_msgs/msg/Twist`): comando manual vindo da dashboard.
- `/rover/esc_pwm` (`std_msgs/msg/Int16`): PWM calculado para o ESC.
- `/rover/servo_pwm` (`std_msgs/msg/Int16`): PWM calculado para o servo de direcao.
- `/rover/telemetry` (`std_msgs/msg/String`): telemetria em JSON para a dashboard.
- `/camera/image/compressed` (`sensor_msgs/msg/CompressedImage`): imagem JPEG da webcam.

## Dependencias ROS2

Instale os pacotes ROS2 esperados pelo launch:

```bash
sudo apt install ros-$ROS_DISTRO-rosbridge-server python3-opencv
```

Se for usar hardware real por GPIO/PWM, substitua ou estenda o no `rover_control.manual_control_node` no ponto onde ele publica os PWM calculados.

## Como rodar com Makefile

Fluxo principal:

```bash
make deps
make run
```

O `make run` compila os pacotes ROS2, sobe o launch do carrinho e inicia a dashboard em `http://localhost:5173`.

Alvos uteis:

```bash
make doctor
make build
make run-ros
make run-dashboard
make clean
```

Parametros podem ser passados como variaveis:

```bash
make run CAMERA_INDEX=0 CAMERA_FPS=20 DASHBOARD_PORT=5173
make run ROSBRIDGE_URL=ws://IP_DO_ROBO:9090
make run ENABLE_CAMERA=false
```

## Como rodar com Docker

O Docker evita depender do `apt` do host para instalar `rosbridge_server`.

```bash
make docker-build
make docker-run
```

Ou diretamente:

```bash
docker compose up --build
```

A dashboard fica em `http://localhost:5173` e o rosbridge em `ws://localhost:9090`.

Para testar sem webcam:

```bash
make docker-run ENABLE_CAMERA=false
```

Para trocar o indice da webcam:

```bash
make docker-run CAMERA_INDEX=2
```

Se acessar a dashboard a partir de outro computador da rede, informe o IP do robo:

```bash
make docker-run ROSBRIDGE_URL=ws://IP_DO_ROBO:9090
```

Se `9090` ou `5173` ja estiverem em uso:

```bash
make docker-run DASHBOARD_PORT=5174 ROSBRIDGE_PORT=9091 ROSBRIDGE_URL=ws://localhost:9091
```

## Como rodar manualmente

Build do workspace:

```bash
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build
source install/setup.bash
```

Suba o ROS2:

```bash
ros2 launch rover_bringup rover.launch.py
```

Em outro terminal, suba a dashboard:

```bash
cd dashboard
npm install
npm run dev
```

Abra a URL mostrada pelo Vite. Por padrao a dashboard conecta em `ws://localhost:9090`.

Para apontar para outro host:

```bash
VITE_ROSBRIDGE_URL=ws://IP_DO_ROBO:9090 npm run dev
```

## Parametros uteis

```bash
ros2 launch rover_bringup rover.launch.py camera_index:=0 camera_fps:=20 max_linear_speed:=1.0 max_angular_speed:=1.0 rosbridge_port:=9090
```

Os limites de PWM ficam no `manual_control_node`:

- `esc_neutral_pwm`: 1500
- `esc_min_pwm`: 1100
- `esc_max_pwm`: 1900
- `servo_center_pwm`: 1500
- `servo_min_pwm`: 1000
- `servo_max_pwm`: 2000
