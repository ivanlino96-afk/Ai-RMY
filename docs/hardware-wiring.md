# Wiring de hardware — Ai-RMY

Este documento se completa a medida que se define el hardware físico exacto. No
asumir pinout desde el orden de cableado — validar aquí y en calibración.

## Confirmado

- **Jetson**: Jetson Nano 4GB Developer Kit.
- **Cámara**: USB (no CSI), sensor 4K. Conectada por USB, no requiere pipeline
  GStreamer (`cv2.VideoCapture(device_index)` en `vision/capture/camera.py`
  funciona tal cual). La Nano no tiene margen para procesar frames a
  resolución nativa 4K: fijar `CameraConfig.frame_width`/`frame_height` bajos
  (ej. 1280x720 o 640x480) en `vision/config.py` en vez de dejar la cámara en
  su resolución nativa. Antes de correr el pipeline en la Jetson, verificar
  con `v4l2-ctl --list-formats-ext -d /dev/video0` si la cámara entrega MJPEG
  (decode liviano) o YUYV crudo (pesado, puede saturar USB2) a esas
  resoluciones, y medir el FPS real resultante.
- **Dev board**: Arduino Uno (ATmega328P, 8-bit AVR @ 16MHz). Ver
  **"Firmware — estado aplicado"** más abajo para el env de PlatformIO.
  Riesgo a validar en banco: 2KB SRAM / 32KB flash es bastante menos que
  módulos anteriores considerados para este proyecto — el stack actual
  (`std::string` + `ArduinoJson` `JsonDocument` + 2x `AccelStepper` + parsing
  NDJSON + watchdog) no está benchmarkeado en memoria todavía. Validar con
  `pio run -e uno` (uso de flash/RAM en el build) antes de dar por cerrado el
  target.
- **Motores**: 2x NEMA17 (pan, tilt).
- **Drivers**: 2x TB6600 (interfaz STEP/DIR, opto-aislada).
- **Alimentación de motores**: fuente externa 24V dedicada (corriente nominal
  aún sin especificar — dimensionar según el NEMA17 elegido y el DIP de
  corriente del TB6600).

## Pendiente de definir (bloquea detalle de wiring)

- [ ] Corriente nominal de los NEMA17 y de la fuente 24V (para setear el DIP de
      corriente del TB6600).
- [ ] Configuración de microstepping de los drivers TB6600 (DIP switches) —
      determina `kStepsPerDegree` en `firmware/src/main.cpp`.
- [ ] Cableado de bobinas del NEMA17 (4/6/8 hilos) — depende del modelo exacto
      comprado; verificar continuidad con multímetro para identificar los 2
      pares de bobina (A+/A-, B+/B-) antes de conectar al TB6600.

## Reglas fijas (no cambian con el hardware específico)

- Los motores se alimentan de una fuente externa dedicada, dimensionada según el
  driver TB6600 y el motor elegido. **Nunca** desde el riel 5V/USB del Arduino.
- Masa común obligatoria entre la fuente de motores, los drivers TB6600 y el
  Arduino (unir GND de la fuente 24V, GND de ambos TB6600 y GND del Arduino).
- Conexión Jetson↔Arduino: USB Serial (mismo cable de datos, no alimentación
  cruzada si el Arduino tiene su propia fuente).

## Diagrama de conexión

```
                    FUENTE 24V (motores)
                    +24V ───────┬──────────────┬───┐
                    GND  ───┐   │              │   │
                             │   │              │   │
                     ┌───────┼───▼──────┐  ┌────▼───┼──────┐
                     │   TB6600 (PAN)   │  │  TB6600 (TILT)│
                     │  VCC        GND  │  │  VCC       GND│
                     │                  │  │               │
                     │  A+ A- B+ B-     │  │  A+ A- B+ B-  │
                     └───┼──┼──┼──┼─────┘  └──┼──┼──┼──┼───┘
                         │  │  │  │           │  │  │  │
                       NEMA17 #1 (pan)      NEMA17 #2 (tilt)
                    (par de bobinas A / par de bobinas B,
                     identificar con multímetro — ver pendientes)

                     PUL+ DIR+ ENA+           PUL+ DIR+ ENA+
                       │    │    │              │    │    │
                       └────┴────┴──────┬───────┴────┴────┘
                                         │
                                    Arduino Uno 5V
                                  (común a ambos drivers)

  Arduino Uno D2 ── PUL- (TB6600 PAN, STEP)
  Arduino Uno D3 ── DIR- (TB6600 PAN, DIR)
  Arduino Uno D4 ── PUL- (TB6600 TILT, STEP)
  Arduino Uno D5 ── DIR- (TB6600 TILT, DIR)
  Arduino Uno D6 ── ENA- (compartido: ambos TB6600 ENA- juntos, opcional)
  Arduino Uno GND ─ GND fuente 24V ── GND ambos TB6600  (masa común)
```

Notas del lado lógico (PUL/DIR/ENA):
- Común a **+5V** del Arduino Uno: a diferencia de un ESP32-C3 (3.3V,
  GPIO no 5V-tolerant), el Uno es lógica 5V nativa — atar el lado `+` a 5V es
  el escenario estándar/más robusto para el opto-acoplador de entrada del
  TB6600 (mejor margen de ruido que a 3.3V), sin riesgo de sobretensión.
  El Uno hunde corriente directamente al poner el pin en LOW (pulso activo)
  — funciona en la mayoría de los módulos TB6600 sin resistencia extra, pero
  **validar en banco** a baja velocidad antes de confiar el wiring final.
- `ENA-` puede dejarse sin conectar si se prefiere: la mayoría de los TB6600
  quedan habilitados por defecto con ENA flotante. Conectarlo a un pin es
  opcional (permite deshabilitar el holding torque desde firmware, no
  implementado todavía en `GimbalControl`).
- D2-D6 se eligieron por ser pines libres sin rol especial en el boot.
  **Evitar** D0/D1 (UART por hardware — es el mismo puerto serial que usa el
  USB Serial hacia la Jetson, no hay un puerto USB nativo separado como en el
  ESP32-C3) y D13 (LED integrado + SPI SCK — un pulso espurio al resetear
  podría enviar un `STEP` fantasma si se usara para esa señal) para
  STEP/DIR/ENA. D2/D3 son además los únicos pines con interrupción externa
  (INT0/INT1) del Uno — no se necesitan sin limit switches, pero quedan
  libres para eso si el diseño cambia más adelante.

## Pinout Arduino Uno

| Señal | Pin Uno | Nota |
| --- | --- | --- |
| STEP (pan) | D2 | |
| DIR (pan) | D3 | |
| STEP (tilt) | D4 | |
| DIR (tilt) | D5 | |
| ENABLE (ambos drivers, compartido) | D6 | opcional, ver notas arriba; no usado desde firmware hoy |
| Común lógico (PUL+/DIR+/ENA+, ambos drivers) | 5V | |
| GND | GND | común con fuente 24V y ambos TB6600 |

Pines libres para expansión futura: D7-D12 (D13 evitado, ver notas), A0-A5.

## Firmware — estado aplicado

`firmware/platformio.ini` apunta a `[env:uno]` (`platform = atmelavr`,
`board = uno`) y `firmware/src/main.cpp` usa D2/D3/D4/D5 (tabla de arriba).
Sigue pendiente de bench:
- `kStepsPerDegree` sigue como placeholder (asume 1/8 microstepping) hasta
  definir el DIP del TB6600.
- Watchdog de `GimbalControl` (`main.cpp`) subido a 3000ms explícitos (antes
  usaba el default de 750ms de la clase): el ping periódico de mantenimiento
  de `SerialLink` (`vision/src/vision/config.py`, `ping_interval_s = 2.0`) es
  más lento que 750ms, así que con el default el watchdog podía dispararse en
  cualquier silencio serial mayor a 750ms — incluyendo un solo comando
  `move_delta` de modo manual que tarde más que eso en completarse. 3000ms
  deja margen sobre los 2.0s de ping sin dejar de ser un watchdog real (ver
  "Modo manual" en `docs/protocol.md`/`app/backend/routers/gimbal.py`).

## Regla udev en la Jetson (path serial estable)

El path `/dev/ttyUSB0`/`/dev/ttyACM0` no está garantizado entre reinicios o
reconexiones. Crear una regla udev que mapee el Arduino por vendor/product ID
(y número de serie si el chip USB-UART lo expone) a un symlink estable, ej.
`/dev/gimbal`. A diferencia del ESP32-C3 (USB nativo, un solo chip), el
identificador USB del Uno depende de **qué variante física** se use — **verificar
con `lsusb` antes de escribir la regla**, no asumir:
- **Arduino Uno R3 original** (ATmega16U2 como puente USB-serial): vendor ID
  `2341` (Arduino LLC), product ID típicamente `0043` (R3) u `0001`
  (revisiones más viejas). Aparece como `/dev/ttyACM0`.
- **Clones** (muy comunes, chip CH340 como puente USB-serial): vendor ID
  `1a86`, product ID `7523`. Aparece como `/dev/ttyUSB0` (puede requerir el
  driver `ch341` en el kernel, ya incluido en la mayoría de las distros
  recientes de JetPack/Ubuntu).

Confirmar con `lsusb` y `udevadm info -a -n /dev/ttyACM0` (o `/dev/ttyUSB0`)
el vendor/product ID exacto antes de escribir la regla — ver
`scripts/provision_jetson.sh` (todavía no creado).
