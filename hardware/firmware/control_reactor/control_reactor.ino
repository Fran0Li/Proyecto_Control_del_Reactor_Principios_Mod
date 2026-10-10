// Control del Reactor - firmware del control físico (Arduino Uno / Nano)
//
// Envía por USB Serial los mensajes de docs/contrato-api-hardware.md:
//   HELLO <id> <version>      al arrancar
//   BTN <boton> PRESS|RELEASE cuando un control cambia de estado
//   HB                        latido cada 1 s
//
// Dos formas de armar el control (cambiar USAR_JOYSTICK):
//   0 = cinco botones: arriba D2, abajo D3, izquierda D4, derecha D5, acción D6  (por defecto)
//   1 = joystick analógico (VRx -> A0, VRy -> A1, SW -> D7) + botón de acción en D6
// En los dos casos los botones van entre el pin y GND (INPUT_PULLUP, sin resistencias).
// El joystick se traduce a los mismos mensajes que los botones, así que el resto del sistema
// no cambia.

#ifndef USAR_JOYSTICK
#define USAR_JOYSTICK 0  // 0 = 5 botones (actual), 1 = joystick
#endif

const char *ID_CONTROL = "CR-PAD-01";
const char *VERSION_FIRMWARE = "1.0";
const unsigned long ANTIRREBOTE_MS = 20;
const unsigned long LATIDO_MS = 1000;
const int PIN_LED = 13;

enum Control { ARRIBA, ABAJO, IZQUIERDA, DERECHA, ACCION, N_CONTROLES };
const char *NOMBRES[N_CONTROLES] = {"UP", "DOWN", "LEFT", "RIGHT", "ACTION"};

#if USAR_JOYSTICK
const int PIN_X = A0;
const int PIN_Y = A1;
const int PIN_ACCION = 6;
const int PIN_CLIC_JOYSTICK = 7;  // presionar el joystick también cuenta como acción
const int CENTRO = 512;
const int UMBRAL_ACTIVAR = 300;     // qué tanto hay que mover la palanca para activar
const int UMBRAL_DESACTIVAR = 200;  // menor que el anterior: evita parpadeos cerca del borde
// Si una dirección sale al revés en el módulo real, cambiar estos valores.
const bool INVERTIR_X = false;
const bool INVERTIR_Y = false;      // false: valor bajo en Y = arriba
#else
const int PINES[N_CONTROLES] = {2, 3, 4, 5, 6};
#endif

bool estable[N_CONTROLES];             // estado ya confirmado y enviado
bool lectura[N_CONTROLES];             // última lectura cruda
unsigned long ultimoCambio[N_CONTROLES];
unsigned long ultimoLatido = 0;

#if USAR_JOYSTICK
// Desplazamiento del eje hacia el lado "positivo" de cada dirección (0 = centro).
int desplazamiento(Control c) {
  int x = analogRead(PIN_X) - CENTRO;
  int y = analogRead(PIN_Y) - CENTRO;
  if (INVERTIR_X) x = -x;
  if (INVERTIR_Y) y = -y;
  switch (c) {
    case ARRIBA: return -y;
    case ABAJO: return y;
    case IZQUIERDA: return -x;
    case DERECHA: return x;
    default: return 0;
  }
}
#endif

bool leerControl(Control c) {
#if USAR_JOYSTICK
  if (c == ACCION) {
    return digitalRead(PIN_ACCION) == LOW || digitalRead(PIN_CLIC_JOYSTICK) == LOW;
  }
  // Histéresis: cuesta más activar que mantener, así no tiembla cerca del umbral.
  int umbral = estable[c] ? UMBRAL_DESACTIVAR : UMBRAL_ACTIVAR;
  return desplazamiento(c) > umbral;
#else
  return digitalRead(PINES[c]) == LOW;
#endif
}

void enviarBoton(Control c, bool presionado) {
  Serial.print("BTN ");
  Serial.print(NOMBRES[c]);
  Serial.println(presionado ? " PRESS" : " RELEASE");
}

void setup() {
  Serial.begin(115200);
#if USAR_JOYSTICK
  pinMode(PIN_ACCION, INPUT_PULLUP);
  pinMode(PIN_CLIC_JOYSTICK, INPUT_PULLUP);
#else
  for (int i = 0; i < N_CONTROLES; i++) pinMode(PINES[i], INPUT_PULLUP);
#endif
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH);  // encendido mientras el control está funcionando

  for (int i = 0; i < N_CONTROLES; i++) {
    estable[i] = false;
    lectura[i] = false;
    ultimoCambio[i] = 0;
  }
  Serial.print("HELLO ");
  Serial.print(ID_CONTROL);
  Serial.print(" ");
  Serial.println(VERSION_FIRMWARE);
}

void loop() {
  unsigned long ahora = millis();

  for (int i = 0; i < N_CONTROLES; i++) {
    Control c = (Control)i;
    bool actual = leerControl(c);
    if (actual != lectura[i]) {  // cambió la lectura: reinicia el antirrebote
      lectura[i] = actual;
      ultimoCambio[i] = ahora;
    }
    // Solo se confirma el cambio si la lectura se mantuvo estable ANTIRREBOTE_MS.
    if (lectura[i] != estable[i] && ahora - ultimoCambio[i] >= ANTIRREBOTE_MS) {
      estable[i] = lectura[i];
      enviarBoton(c, estable[i]);
    }
  }

  if (ahora - ultimoLatido >= LATIDO_MS) {
    ultimoLatido = ahora;
    Serial.println("HB");
  }
}
