# Ai-RMY — Instrucciones para agentes

## Alcance del producto

Ai-RMY es un gimbal pan-tilt de seguimiento facial:

- Controlador de movimiento: ESP32 (Arduino framework, PlatformIO).
- Actuadores: 2 motores a pasos (pan, tilt) vía drivers TB660 (interfaz STEP/DIR).
- Visión: Jetson Nano corriendo detección facial (OpenCV YuNet) + reconocimiento
  (embedding ONNX + match coseno contra rostros guardados).
- Cliente: dashboard web (React + Tailwind CSS), servido por el backend FastAPI que
  corre en la propia Jetson.
- Comunicación motor: USB Serial (NDJSON) entre Jetson y ESP32. Ver `docs/protocol.md`
  como única fuente de verdad del protocolo — firmware y vision deben implementarlo
  idéntico.
- Alcance de red: solo LAN. Sin acceso remoto/cloud, sin autenticación en el MVP.

El producto permite: seguimiento automático de un rostro (centrado del gimbal),
gestión de rostros conocidos (alta/baja/edición con foto), vista de cámara en vivo
con overlay de detección (bounding box + nombre o "Unknown"), y estado del gimbal en
tiempo real.

## Mecánica de referencia

- Ejes: `pan` (rotación horizontal), `tilt` (inclinación vertical).
- Sin limit switches en el MVP: el "home" es la posición mecánica física al encender.
  No asumir una posición absoluta calibrada — puede haber deriva en sesiones largas.
- Ángulos y deltas de movimiento se expresan en grados (`float`) en el protocolo.
- La correspondencia física driver↔motor↔eje debe quedar documentada en
  `docs/hardware-wiring.md` y no asumirse desde el orden de cableado.

## Reglas de seguridad obligatorias

- El ESP32 es la autoridad final: toda orden recibida por serial debe validar
  límites suaves de pan/tilt antes de mover los motores, sin depender de que la
  Jetson ya los haya validado.
- Ante ausencia de un comando válido por ~500ms-1s (watchdog), mantener la posición
  actual — nunca extrapolar movimiento sin confirmación reciente del host.
- `stop` tiene la máxima prioridad y corta cualquier movimiento en curso de inmediato.
- Los motores se alimentan desde una fuente externa propia (acorde al driver TB660),
  con masa común al ESP32. Nunca alimentar los motores desde el riel 5V/USB del ESP32.
- No commitear nunca datos biométricos: fotos de rostros y `faces.db` viven en
  `vision/data/` (gitignored). Los modelos `.onnx` tampoco se commitean (se descargan
  vía `scripts/download_models.sh`).
- No afirmar posición angular absoluta sin homing: sin limit switches, los ángulos
  reportados son relativos al encendido, no una referencia calibrada.

## Arquitectura de software

### Firmware (`firmware/`)

- PlatformIO + Arduino framework, target ESP32.
- `AccelStepper` para control de los 2 ejes; si aparece jitter con la carga de
  serial+watchdog, la ruta de mejora documentada es `FastAccelStepper` (no reescribir
  desde cero, migrar el wrapper en `lib/GimbalControl`).
- `lib/SerialProtocol/` parsea y serializa NDJSON según `docs/protocol.md` — no
  duplicar la lógica del protocolo en `main.cpp`.
- `lib/GimbalControl/` encapsula límites suaves, watchdog y homing manual.

### Vision (`vision/`)

- Librería Python independiente y testeable, sin dependencias de FastAPI/web —
  `app/backend` la importa en el mismo proceso, no por red.
- `detection/`: wrapper de YuNet (ONNX). `recognition/`: embedding ONNX +
  matcher coseno (SQLite, sin vector DB — no introducir FAISS/Milvus a esta escala).
- `tracking/`: controlador P con deadband (no escalar a PID sin evidencia de
  oscilación real).
- `serial_link/`: cliente pyserial hablando `docs/protocol.md`; debe reconectar con
  backoff si el dispositivo serial desaparece (ver reglas de udev en
  `docs/hardware-wiring.md`).
- Compatibilidad: el target de despliegue (Jetson Nano, JetPack 4.6) corre
  **Python 3.6** — evitar sintaxis/librerías que requieran ≥3.7 (ej. no usar
  `dataclasses` sin backport, no asumir `f-string` avanzados de 3.8+).

### Backend (`app/backend/`)

- FastAPI. Importa `vision` en el mismo proceso y corre el pipeline como hilo de
  background con estado compartido (frame anotado + evento de detección).
- Sin autenticación en el MVP (deja un stub `get_current_user` sin efecto para no
  reescribir rutas cuando se agregue).
- Sirve el build de `app/frontend` vía `StaticFiles` en producción.

### Frontend (`app/frontend/`)

- React + Tailwind CSS. Sin Redux/Zustand — React Query para estado de servidor.
- Estética táctica/HUD: fondo oscuro, bordes finos, fuente monoespaciada,
  `CornerBracketPanel`/`StatusBadge` como primitivos reutilizables (construir y
  validar visualmente antes de las páginas reales).
- No mezclar lógica de protocolo/parsing con componentes de presentación.

## Pruebas mínimas

- Firmware: tests nativos de PlatformIO para parseo NDJSON y validación de límites,
  antes de flashear a hardware real.
- Vision: validar por separado detección (YuNet) y reconocimiento (embeddings ONNX)
  antes de integrar el loop de tracking o el envío serial.
- Antes de cualquier prueba física con motores: velocidad baja y límites
  conservadores.

## Convenciones

- Protocolo serial versionado: todo mensaje incluye `"proto":1`.
- Coordenadas de imagen: origen (0,0) en la esquina superior izquierda del frame,
  ejes en píxeles.
- No mezclar lógica de UI con protocolo serial, visión o control de hardware.
- `docs/protocol.md` es la única fuente de verdad del protocolo — cualquier cambio
  se documenta ahí primero y luego se refleja en firmware y vision.
