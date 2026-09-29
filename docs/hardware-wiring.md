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
- **Dev board**: Arduino MKR Zero (SAMD21, ARM Cortex-M0+ @ 48MHz, lógica
  **3.3V y no tolerante a 5V**). Ver **"Firmware — estado aplicado"** más abajo
  para el env de PlatformIO. 32KB SRAM / 256KB flash da bastante margen sobre
  el Arduino Uno considerado antes (el stack actual — `std::string` +
  `ArduinoJson` `JsonDocument` + 2x `AccelStepper` + parsing NDJSON + watchdog
  — no debería ser un problema de memoria). El riesgo a validar en banco ahora
  es otro: cada pin del MKR Zero solo puede entregar/hundir ~7mA, muy por
  debajo de lo que un opto-acoplador de TB6600 pensado para 5V puede necesitar
  para disparar de forma confiable — de ahí el esquema de wiring (común `+`
  a 5V, MCU solo hunde corriente) descrito más abajo. Validar con
  `pio run -e mkrzero` (compila, uso de flash/RAM) y en banco a baja
  velocidad antes de dar por cerrado el target.
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
                       └────┴────┼──────┬───────┴────┴────┘
                                  │      │
                              (sin conectar,      MKR Zero +5V
                            ENA flotante = OK)   (común a ambos drivers)

  MKR Zero D1 ── PUL- (TB6600 PAN, STEP)
  MKR Zero D2 ── DIR- (TB6600 PAN, DIR)
  MKR Zero D3 ── PUL- (TB6600 TILT, STEP)
  MKR Zero D4 ── DIR- (TB6600 TILT, DIR)
  ENA+ / ENA- (ambos drivers) ── sin conectar (ver notas: habilitados por defecto)
  MKR Zero GND ─ GND fuente 24V ── GND ambos TB6600  (masa común)
```

Notas del lado lógico (PUL/DIR/ENA):
- El MKR Zero es lógica **3.3V y no tolerante a 5V**, con un límite de
  ~7mA por pin — muy poco margen para alimentar directamente el lado `+`
  de un opto-acoplador de TB6600 dimensionado para 5V (a diferencia del
  Arduino Uno, que era 5V nativo y podía hacerlo sin margen de ruido
  reducido). Por eso el esquema se invierte respecto al de un Uno: el lado
  `+` de PUL/DIR de ambos drivers va al pin **`+5V`** propio del MKR Zero
  (rail común, no un pin digital — no lo genera un regulador propio del
  MKR Zero sino que viene del USB, ver hoja de datos), y cada pin digital
  (D1-D4) solo **hunde corriente** poniéndose en LOW para el pulso activo,
  igual que antes pero con los roles `+`/`-` intercambiados. **Validar en
  banco** a baja velocidad que el opto-acoplador dispara de forma confiable
  con esta corriente antes de confiar el wiring final — si no dispara con
  margen, la alternativa es una resistencia limitadora recalculada para
  3.3V o un driver de nivel intermedio (no implementado, ver riesgo en
  "Confirmado" arriba).
- `ENA+`/`ENA-` se dejan **sin conectar** en ambos drivers: la mayoría de los
  TB6600 quedan habilitados (holding torque activo) por defecto con ENA
  flotante — decisión confirmada para este proyecto por simplicidad. No hay
  forma de deshabilitar el torque desde firmware con este wiring (no
  implementado en `GimbalControl` de todas formas).
- D1-D4 se eligieron por ser pines libres sin rol especial de arranque en el
  MKR Zero. A diferencia del Uno, el Serial que habla con la Jetson es
  **USB nativo (USB-CDC)** en el SAMD21, no una UART sobre D0/D1 — por lo
  tanto D0/D1 quedan libres de cualquier conflicto con el enlace serial (se
  evitan igual, por si se necesitan a futuro para I2S). D13/D14 se evitan
  porque son la UART física `Serial1` del MKR Zero (no usada hoy, pero se
  deja libre por si hiciera falta telemetría/depuración separada del enlace
  USB con la Jetson).

## Pinout Arduino MKR Zero

| Señal | Pin MKR Zero | Nota |
| --- | --- | --- |
| STEP (pan) | D1 | hunde corriente (LOW = pulso activo) |
| DIR (pan) | D2 | hunde corriente |
| STEP (tilt) | D3 | hunde corriente |
| DIR (tilt) | D4 | hunde corriente |
| ENABLE (ambos drivers) | — | sin conectar, ver notas arriba; no usado desde firmware hoy |
| Común lógico (PUL+/DIR+, ambos drivers) | +5V | rail común del MKR Zero, no un pin digital |
| GND | GND | común con fuente 24V y ambos TB6600 |

Pines libres para expansión futura: D0, D5-D12 (D13/D14 evitados, ver
notas), A0-A6.

## Firmware — estado aplicado

`firmware/platformio.ini` apunta a `[env:mkrzero]` (`platform = atmelsam`,
`board = mkrzero`) y `firmware/src/main.cpp` usa D1/D2/D3/D4 (tabla de
arriba). Sigue pendiente de bench:
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
`/dev/gimbal`.

El MKR Zero usa **USB nativo (USB-CDC) del SAMD21**, no un puente USB-serial
externo como el ATmega16U2 del Uno o un CH340 de clon — un solo chip, un solo
identificador USB, sin ambigüedad de "variante física" a verificar. El vendor
ID `2341` (Arduino LLC) está confirmado (fuente oficial Arduino); el product
ID específico del MKR Zero **no está verificado aquí todavía** — no asumirlo
de una búsqueda no confirmada. Aparece como `/dev/ttyACM0`.

Confirmar con `lsusb` y `udevadm info -a -n /dev/ttyACM0` el vendor/product ID
exacto antes de escribir la regla — ver `scripts/provision_jetson.sh`
(todavía no creado).
