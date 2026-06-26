import threading
import time

import serial
from serial import SerialException

SERVO_RIGHT_PWM = 1000
SERVO_CENTER_PWM = 1500
SERVO_LEFT_PWM = 2000
ESC_STOP_PWM = 1500
ESC_MIN_MOVE_PWM = 1580


def describe_servo_position(pwm_value):
    if pwm_value == SERVO_RIGHT_PWM:
        return "direita total"
    if pwm_value == SERVO_CENTER_PWM:
        return "centro"
    if pwm_value == SERVO_LEFT_PWM:
        return "esquerda total"
    if pwm_value < SERVO_CENTER_PWM:
        return "direita"
    return "esquerda"


def describe_esc_state(pwm_value):
    if pwm_value == ESC_STOP_PWM:
        return "parado"
    if ESC_STOP_PWM < pwm_value < ESC_MIN_MOVE_PWM:
        return "zona morta"
    if pwm_value >= ESC_MIN_MOVE_PWM:
        return "andando"
    return "reverso/freio"


class ArduinoBridge:
    def __init__(self, serial_port="/dev/ttyUSB0", baud_rate=115200):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial_conn = None
        self.serial_failed = False
        self.last_esc_pwm = ESC_STOP_PWM
        self.last_servo_pwm = SERVO_CENTER_PWM
        self._lock = threading.Lock()

        try:
            self.serial_conn = serial.Serial(self.serial_port, self.baud_rate, timeout=1, write_timeout=0.1)
            time.sleep(2)
            print(f"[INFO] Conectado ao Arduino na porta {self.serial_port}")
        except Exception as e:
            print(f"[ERRO] Falha ao ligar ao Arduino: {e}")

    @property
    def is_connected(self):
        return bool(self.serial_conn and self.serial_conn.is_open and not self.serial_failed)

    def _write(self, comando, descricao):
        """Escreve na serial e invalida a conexao se o dispositivo falhar."""
        with self._lock:
            if not self.serial_conn or not self.serial_conn.is_open or self.serial_failed:
                print("[ERRO] Porta serial nao esta aberta.")
                return False

            try:
                self.serial_conn.write(comando)
                return True
            except SerialException as e:
                self.serial_failed = True
                print(f"[ERRO] Falha ao enviar {descricao}: {e}")
                print("[ERRO] Verifique cabo, porta e reset do Arduino. Encerrando conexao serial.")
                try:
                    self.serial_conn.close()
                except SerialException:
                    pass
                return False

    def send_esc(self, pwm_value):
        """Envia o sinal PWM para o ESC."""
        comando = f"E{pwm_value}\n"
        ok = self._write(comando.encode("utf-8"), f"ESC {pwm_value}")
        if ok:
            self.last_esc_pwm = pwm_value
            print(f"[ENVIADO] ESC -> {pwm_value} ({describe_esc_state(pwm_value)})")
        return ok

    def send_servo(self, pwm_value):
        """Envia o sinal PWM para o servo."""
        comando = f"S{pwm_value}\n"
        ok = self._write(comando.encode("utf-8"), f"Servo {pwm_value}")
        if ok:
            self.last_servo_pwm = pwm_value
            print(f"[ENVIADO] Servo -> {pwm_value} ({describe_servo_position(pwm_value)})")
        return ok

    def calibrate_esc(self):
        """Inicia a rotina de calibracao do ESC no firmware do Arduino."""
        ok = self._write(b"C\n", "calibracao do ESC")
        if ok:
            print("[ENVIADO] Calibracao do ESC iniciada no Arduino.")
        return ok

    def stop_all(self):
        """Envia neutro para ESC e servo."""
        if self.is_connected:
            print("[INFO] Parando motores (PWM 1500)...")
            ok = self._write(b"E1500\nS1500\n", "parada de emergencia")
            if ok:
                self.last_esc_pwm = ESC_STOP_PWM
                self.last_servo_pwm = SERVO_CENTER_PWM
            return ok
        return False

    def close(self):
        """Fecha a conexao com seguranca."""
        if self.serial_conn and self.serial_conn.is_open:
            self.stop_all()
            time.sleep(0.5)
            self.serial_conn.close()
            print("[INFO] Conexao serial encerrada.")

    def status(self):
        return {
            "connected": self.is_connected,
            "serial_failed": self.serial_failed,
            "serial_port": self.serial_port,
            "baud_rate": self.baud_rate,
            "esc_pwm": self.last_esc_pwm,
            "esc_state": describe_esc_state(self.last_esc_pwm),
            "servo_pwm": self.last_servo_pwm,
            "servo_position": describe_servo_position(self.last_servo_pwm),
        }
