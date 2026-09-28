# Protocolo serial Jetson ↔ Arduino Uno

Fuente única de verdad. `firmware/lib/SerialProtocol` y `vision/src/vision/serial_link`
deben implementar exactamente esto — cualquier cambio se hace aquí primero.

- Transporte: USB Serial, 115200 baudios.
- Formato: una línea de JSON por mensaje (NDJSON), terminada en `\n`.
- Todo mensaje incluye `"proto": 1`.

## Jetson → Arduino Uno

| `cmd` | Campos | Descripción |
| --- | --- | --- |
| `move_delta` | `pan` (float, grados), `tilt` (float, grados), `seq` (int) | Corrección incremental. Usado por el loop de tracking automático y por el modo manual (jog de un solo eje: pasar 0 en el eje que no se quiere mover). |
| `goto` | `pan_deg` (float), `tilt_deg` (float), `seq` (int) | Movimiento a un ángulo absoluto (re-centrado manual). |
| `stop` | — | Corta cualquier movimiento en curso. Máxima prioridad. |
| `home` | — | Redefine la posición física actual como origen (0,0). No mueve motores. No hay limit switches (ver `AGENTS.md`); disponible también como botón "Home" en la UI. |
| `ping` | — | Chequeo de liveness. |

Ejemplo:
```json
{"proto":1,"cmd":"move_delta","pan":-1.2,"tilt":0.4,"seq":102}
```

## Arduino Uno → Jetson

Ack inmediato por comando recibido, más telemetría periódica (~10 Hz) aunque no
haya comandos entrantes:

```json
{"proto":1,"ok":true,"seq":102,"pan_deg":12.4,"tilt_deg":-3.1,"moving":true,"homed":true}
```

- `ok`: `false` si el comando fue rechazado (ej. excede límites suaves) — en ese
  caso incluir `"error":"<motivo>"`.
- `pan_deg`/`tilt_deg`: ángulo relativo al origen (0,0) vigente — la posición al
  encender, o la última posición marcada con `home` — nunca una referencia
  absoluta calibrada (no hay limit switches, ver `AGENTS.md`).
- `homed`: `true` en cuanto el firmware arranca (la posición de encendido ES el
  origen por definición) y sigue `true` después de cada `home` explícito. No
  representa una posición absoluta calibrada, solo que existe un origen
  vigente.

## Watchdog

Si el Arduino Uno no recibe un mensaje válido dentro del timeout configurado, debe
mantener la posición actual (no continuar extrapolando movimiento) y
reportarlo en la telemetría (`moving: false`).

Timeout actual: 3000ms (`firmware/src/main.cpp`, parámetro `watchdogTimeoutMs`
de `GimbalControl`). Debe mantenerse **por encima** de `ping_interval_s` del
lado Jetson (`vision/src/vision/config.py`, hoy 2.0s) para que el ping
periódico de mantenimiento sea suficiente para evitar un disparo falso — esto
importa en particular para el modo manual, donde un único `move_delta` puede
tardar en completarse más que el intervalo de ping.

## Límites suaves

Configurados en firmware (`lib/GimbalControl`), no en la Jetson. Todo `move_delta`
o `goto` que exceda el rango configurado se recorta o rechaza (`ok: false`) — el
Arduino Uno nunca confía en que el lado Jetson ya validó el rango.
