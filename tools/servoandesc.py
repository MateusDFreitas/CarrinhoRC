import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from carrinho_serial import ArduinoBridge


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controle manual de ESC e servo via USB serial.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Porta serial do Arduino (ex: /dev/ttyUSB0 ou /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate da serial")
    args = parser.parse_args()

    bridge = ArduinoBridge(serial_port=args.port, baud_rate=args.baud)

    if bridge.serial_conn is None:
        print("[ERRO] Saindo do programa pois o Arduino nao foi encontrado.")
        sys.exit(1)

    print("\n" + "=" * 40)
    print("      TESTE MANUAL DE MOTORES")
    print("=" * 40)
    print("Instrucoes:")
    print("  - Digite 'E <valor>' para controlar o ESC")
    print("    E 1500 = parado | E 1580+ = comeca a andar")
    print("  - Digite 'S <valor>' para controlar o Servo")
    print("    S 1000 = direita total | S 1500 = centro | S 2000 = esquerda total")
    print("  - Digite 'P' para Parada de Emergencia (Neutro)")
    print("  - Digite 'C' para iniciar a calibracao do ESC no Arduino")
    print("  - Digite 'sair' para encerrar o programa.")
    print("=" * 40 + "\n")

    try:
        while True:
            entrada = input("Comando: ").strip().upper()

            if entrada == "SAIR":
                break

            if entrada == "P":
                bridge.stop_all()
                if bridge.serial_failed:
                    break
                continue

            if entrada == "C":
                bridge.calibrate_esc()
                if bridge.serial_failed:
                    break
                continue

            partes = entrada.split()
            if len(partes) == 2:
                motor = partes[0]
                try:
                    valor = int(partes[1])
                    if motor == "E":
                        bridge.send_esc(valor)
                    elif motor == "S":
                        bridge.send_servo(valor)
                    else:
                        print("-> [ERRO] Motor invalido. Use 'E' ou 'S'.")
                    if bridge.serial_failed:
                        break
                except ValueError:
                    print("-> [ERRO] O valor do PWM deve ser um numero (ex: 1500).")
            else:
                print("-> [ERRO] Formato invalido. Use letra e numero com espaco (ex: E 1600).")

    except KeyboardInterrupt:
        print("\n[INFO] Encerramento forcado detectado (CTRL+C)...")
    finally:
        bridge.close()
