# Ai-RMY

Gimbal pan-tilt de seguimiento facial: ESP32 (motores a pasos) + Jetson Nano
(visión/reconocimiento) + dashboard web (React) para gestionar rostros y ver la
cámara en vivo.

Ver [`AGENTS.md`](./AGENTS.md) para el alcance completo del producto, reglas de
seguridad y arquitectura. Ver [`docs/architecture.md`](./docs/architecture.md) para
el diseño detallado y [`docs/protocol.md`](./docs/protocol.md) para el protocolo
serial entre Jetson y ESP32.

## Estructura

- `firmware/` — proyecto PlatformIO (ESP32, control de motores a pasos).
- `vision/` — pipeline de visión en Python (Jetson Nano): detección, reconocimiento,
  tracking, protocolo serial, almacenamiento.
- `app/backend/` — FastAPI, importa `vision` en el mismo proceso, expone la API y
  sirve el dashboard.
- `app/frontend/` — dashboard React + Tailwind CSS.
- `docs/` — arquitectura, protocolo serial, wiring de hardware.
- `scripts/` — utilidades (descarga de modelos, flasheo de firmware, provisión de
  la Jetson).

## Hardware (BOM inicial)

| Componente | Notas |
| --- | --- |
| ESP32 (dev board) | USB Serial hacia la Jetson |
| Jetson Nano | JetPack 4.6, cámara CSI/USB |
| 2x motor a pasos | pan / tilt |
| 2x driver TB660 | interfaz STEP/DIR |
| Fuente externa para motores | NO alimentar motores desde el riel 5V del ESP32 |

## Quickstart por subproyecto

Cada subcarpeta (`firmware/`, `vision/`, `app/backend/`, `app/frontend/`) tendrá su
propio quickstart a medida que se vaya implementando. Este README se irá
completando en paralelo al desarrollo.

## Estado

Proyecto en fase de scaffolding inicial — ver el plan de arquitectura para el
detalle de MVP vs. fases futuras.
# Ai-RMY
# Ai-RMY
