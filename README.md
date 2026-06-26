# CarrinhoRC

Controle em Python puro para um carrinho RC com Arduino ligado por USB, ESC e servo de direcao.

A Jetson envia comandos pela porta serial para o Arduino, e o Arduino deve interpretar linhas neste formato:

- `E1500`: PWM do ESC.
- `S1500`: PWM do servo.

Cada comando termina com `\n`.

O firmware tambem aceita `E 1500`, `S 1500`, `P` e `C`.

Convencao atual do servo:

- `S1000`: direita total.
- `S1500`: centro.
- `S2000`: esquerda total.

Convencao atual do ESC:

- `E1500`: totalmente parado/neutro.
- `E1580` em diante: minimo para comecar a andar.

## Arquivos principais

- `dashboard`: dashboard React original adaptada para controlar ESC e servo via USB serial.
- `backend/server.py`: backend Python que serve a dashboard compilada e expõe a API serial e o stream da camera.
- `backend/camera_stream.py`: captura a camera com OpenCV e expõe frames MJPEG.
- `backend/carrinho_serial.py`: ponte serial compartilhada entre dashboard e terminal.
- `tools/servoandesc.py`: terminal interativo para teste manual.
- `arduino/CarrinhoRCFirmware/CarrinhoRCFirmware.ino`: firmware Arduino nao bloqueante para receber comandos em tempo real.

## Estrutura

```text
arduino/                    firmware para o Arduino Nano
backend/                    servidor HTTP e ponte serial em Python
dashboard/                  frontend React/Vite
tools/                      ferramentas de teste manual
Dockerfile                  imagem para rodar backend + dashboard
docker-compose.yml          execucao Docker com acesso a /dev
Makefile                    comandos locais de desenvolvimento
requirements.txt            dependencias Python
```

## Dependencias

```bash
make deps
```

Isto instala `pyserial` e `opencv-python-headless` para o stream da camera.

Na Jetson, se a instalacao do OpenCV via pip nao funcionar bem, use o pacote do sistema:

```bash
sudo apt install python3-opencv
```

A dashboard esta travada em Vite 4 para funcionar com Node 16, como o `v16.20.2` comum na Jetson. Se o `npm audit` sugerir `npm audit fix --force`, nao use esse comando sem atualizar o Node antes, porque ele pode trocar o Vite por uma versao que exige Node 18+.

## Verificar ambiente

```bash
make doctor
```

O comando verifica Python, `pyserial`, OpenCV, portas seriais como `/dev/ttyUSB0` e `/dev/ttyACM0`, e cameras como `/dev/video0`.

## Rodar

```bash
make run
```

Abra:

```text
http://localhost:8000
```

O `make run` instala dependencias npm quando necessario, compila a dashboard React e sobe o backend Python.

Por padrao usa:

- Porta: `/dev/ttyUSB0`
- Baud rate: `115200`
- Camera: `/dev/video0`
- Video: `640x480 @ 20fps`
- Dashboard: `http://localhost:8000`

Para trocar:

```bash
make run SERIAL_PORT=/dev/ttyACM0 BAUD_RATE=115200 DASHBOARD_PORT=8001
```

Para trocar a camera:

```bash
make run CAMERA_DEVICE=/dev/video1 CAMERA_WIDTH=1280 CAMERA_HEIGHT=720 CAMERA_FPS=15
```

Ou diretamente a dashboard:

```bash
python3 backend/server.py --port /dev/ttyUSB0 --baud 115200 --http-port 8000 --camera-device /dev/video0
```

O stream fica em:

```text
http://localhost:8000/api/camera/stream
```

Para usar o terminal interativo:

```bash
make run-serial
```

## Comandos no terminal

Dentro do programa:

```text
E 1600
S 1200
P
C
sair
```

- `E <valor>` controla o ESC.
- `S <valor>` controla o servo.
- `P` envia parada/neutro: `E1500` e `S1500`.
- `C` inicia a calibracao do ESC no firmware do Arduino.
- `sair` encerra o programa.

Para aceleracao:

- `E 1500`: totalmente parado.
- `E 1580`: minimo para comecar a andar.
- `E 1600` ou mais: andando com mais potencia.

Para direcao:

- `S 1000`: direita total.
- `S 1500`: centro.
- `S 2000`: esquerda total.

## Permissao da porta serial

Se aparecer erro de permissao na Jetson/Linux, adicione seu usuario ao grupo `dialout`:

```bash
sudo usermod -aG dialout $USER
```

Depois saia da sessao e entre novamente.

## Firmware Arduino

Abra `arduino/CarrinhoRCFirmware/CarrinhoRCFirmware.ino` na Arduino IDE e grave na placa.

Pinos usados:

- Servo de direcao: `D9`.
- ESC: `D10`.

O firmware nao usa `Serial.parseInt()`, porque ele pode bloquear o loop esperando timeout quando a serial chega incompleta. O parser atual le byte a byte, processa comandos terminados em nova linha e tem failsafe: se o ESC estiver andando e ficar sem comando por 500 ms, volta para `E1500`.

## Calibracao do ESC

No Arduino Nano ATmega168P, a calibracao fica no proprio `CarrinhoRCFirmware.ino`. Na Arduino IDE, use:

- Board: `Arduino Nano`
- Processor: `ATmega168`
- Baud do Monitor Serial: `115200`

O firmware usa o pino `D10` para o ESC. Fluxo:

1. Desconecte a bateria/alimentacao de potencia do ESC.
2. Grave `arduino/CarrinhoRCFirmware/CarrinhoRCFirmware.ino` e deixe o Arduino ligado no USB.
3. Abra o Monitor Serial em `115200`.
4. Envie `C`.
5. O Arduino passa a enviar `2000 us`.
6. Conecte a bateria do ESC.
7. Depois dos bipes, envie qualquer caractere no Monitor Serial.
8. O Arduino envia `1000 us`.
9. Depois dos bipes finais, envie qualquer caractere novamente.
10. O Arduino volta para `1500 us` neutro/parado e retorna ao modo normal de controle.

## Docker opcional

O Docker tambem pode rodar o controle serial:

```bash
make docker-build
make docker-run SERIAL_PORT=/dev/ttyUSB0
```

Abra `http://localhost:8000`.

Para controle de hardware real, normalmente e mais simples rodar direto na Jetson com `make run`.
