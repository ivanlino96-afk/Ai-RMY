# Protocolo serial Jetson ↔ ESP32

Fuente única de verdad. `firmware/lib/SerialProtocol` y `vision/src/vision/serial_link`
deben implementar exactamente esto — cualquier cambio se hace aquí primero.

- Transporte: USB Serial, 115200 baudios.
- Formato: una línea de JSON por mensaje (NDJSON), terminada en `\n`.
- Todo mensaje incluye `"proto": 1`.

## Jetson → ESP32

| `cmd` | Campos | Descripción |
| --- | --- | --- |
| `move_delta` | `pan` (float, grados), `tilt` (float, grados), `seq` (int) | Corrección incremental del loop de tracking. |
| `goto` | `pan_deg` (float), `tilt_deg` (float), `seq` (int) | Movimiento a un ángulo absoluto (re-centrado manual). |
| `stop` | — | Corta cualquier movimiento en curso. Máxima prioridad. |
| `home` | — | Dispara rutina de homing (no-op en MVP sin limit switches; reservado). |
| `ping` | — | Chequeo de liveness. |

Ejemplo:
```json
{"proto":1,"cmd":"move_delta","pan":-1.2,"tilt":0.4,"seq":102}
```

## ESP32 → Jetson

Ack inmediato por comando recibido, más telemetría periódica (~10 Hz) aunque no
haya comandos entrantes:

```json
{"proto":1,"ok":true,"seq":102,"pan_deg":12.4,"tilt_deg":-3.1,"moving":true,"homed":false}
```

- `ok`: `false` si el comando fue rechazado (ej. excede límites suaves) — en ese
  caso incluir `"error":"<motivo>"`.
- `pan_deg`/`tilt_deg`: ángulo relativo al encendido (sin homing, no es una
  referencia absoluta calibrada — ver `AGENTS.md`).
- `homed`: `false` en el MVP (sin limit switches). Reservado para cuando se agregue
  homing físico.

## Watchdog

Si el ESP32 no recibe un mensaje válido en 500ms–1s, debe mantener la posición
actual (no continuar extrapolando movimiento) y reportarlo en la telemetría
(`moving: false`).

## Límites suaves

Configurados en firmware (`lib/GimbalControl`), no en la Jetson. Todo `move_delta`
o `goto` que exceda el rango configurado se recorta o rechaza (`ok: false`) — el
ESP32 nunca confía en que el lado Jetson ya validó el rango.
