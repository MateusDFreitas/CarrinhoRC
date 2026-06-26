#include <Servo.h>

const byte SERVO_PIN = 9;
const byte ESC_PIN = 10;

const int SERVO_MIN_PWM = 1000;
const int SERVO_CENTER_PWM = 1500;
const int SERVO_MAX_PWM = 2000;

const int ESC_MIN_PWM = 1000;
const int ESC_STOP_PWM = 1500;
const int ESC_MAX_PWM = 2000;

const unsigned long ARM_TIME_MS = 3000;
const unsigned long FAILSAFE_TIMEOUT_MS = 500;

Servo steeringServo;
Servo esc;

char lineBuffer[16];
byte lineLength = 0;

int currentServoPwm = SERVO_CENTER_PWM;
int currentEscPwm = ESC_STOP_PWM;
unsigned long lastCommandMs = 0;

void clearSerialInput() {
  while (Serial.available() > 0) {
    Serial.read();
  }
}

void waitForSerialConfirmation() {
  while (Serial.available() == 0) {
    delay(10);
  }
  clearSerialInput();
}

void applyServo(int pwm) {
  pwm = constrain(pwm, SERVO_MIN_PWM, SERVO_MAX_PWM);
  if (pwm != currentServoPwm) {
    currentServoPwm = pwm;
    steeringServo.writeMicroseconds(currentServoPwm);
  }
}

void applyEsc(int pwm) {
  pwm = constrain(pwm, ESC_MIN_PWM, ESC_MAX_PWM);
  if (pwm != currentEscPwm) {
    currentEscPwm = pwm;
    esc.writeMicroseconds(currentEscPwm);
  }
}

void stopAll() {
  applyEsc(ESC_STOP_PWM);
  applyServo(SERVO_CENTER_PWM);
}

void calibrateEsc() {
  clearSerialInput();

  Serial.println(F("Calibracao do ESC - Arduino Nano ATmega168P"));
  Serial.println(F("Pino ESC: D10"));
  Serial.println(F("1. Desconecte a bateria/alimentacao de potencia do ESC."));
  Serial.println(F("2. Mantenha o USB ligado no Arduino."));
  Serial.println(F("3. O Arduino vai enviar 2000 us agora."));
  Serial.println(F("4. Conecte a bateria do ESC."));
  Serial.println(F("5. Apos os bipes, envie qualquer caractere no Monitor Serial."));

  applyEsc(ESC_MAX_PWM);
  waitForSerialConfirmation();

  Serial.println(F("Sinal minimo enviado: 1000 us."));
  Serial.println(F("Aguarde os bipes de confirmacao."));
  Serial.println(F("Depois envie qualquer caractere para finalizar em neutro."));

  applyEsc(ESC_MIN_PWM);
  waitForSerialConfirmation();

  stopAll();
  lastCommandMs = millis();

  Serial.println(F("Sinal neutro enviado: 1500 us."));
  Serial.println(F("Calibracao concluida. Firmware voltou ao modo de controle."));
}

void processLine(char *line) {
  while (*line == ' ' || *line == '\t') {
    line++;
  }

  char target = line[0];
  if (target >= 'a' && target <= 'z') {
    target -= 32;
  }

  if (target == 'P') {
    stopAll();
    lastCommandMs = millis();
    return;
  }

  if (target == 'C') {
    calibrateEsc();
    return;
  }

  if (target != 'E' && target != 'S') {
    return;
  }

  line++;
  while (*line == ' ' || *line == '\t' || *line == ':' || *line == '=') {
    line++;
  }

  bool negative = false;
  if (*line == '-') {
    negative = true;
    line++;
  }

  int value = 0;
  bool hasDigit = false;
  while (*line >= '0' && *line <= '9') {
    hasDigit = true;
    value = (value * 10) + (*line - '0');
    line++;
  }

  if (!hasDigit || negative) {
    return;
  }

  if (target == 'E') {
    applyEsc(value);
  } else {
    applyServo(value);
  }

  lastCommandMs = millis();
}

void readSerialNonBlocking() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();

    if (c == '\n' || c == '\r') {
      if (lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        processLine(lineBuffer);
        lineLength = 0;
      }
      continue;
    }

    if (lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = c;
    } else {
      lineLength = 0;
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(5);

  steeringServo.attach(SERVO_PIN);
  esc.attach(ESC_PIN);

  stopAll();
  delay(ARM_TIME_MS);
  lastCommandMs = millis();

  Serial.println(F("CarrinhoRC pronto."));
  Serial.println(F("Comandos: E1500, S1500, P, C"));
}

void loop() {
  readSerialNonBlocking();

  if (millis() - lastCommandMs > FAILSAFE_TIMEOUT_MS && currentEscPwm != ESC_STOP_PWM) {
    applyEsc(ESC_STOP_PWM);
  }
}
