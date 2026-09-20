# Arquitectura — Ai-RMY

Ver `AGENTS.md` para el resumen normativo (reglas de seguridad, convenciones). Este
documento es la referencia detallada de diseño.

## Visión general

```
[Cámara] -> [Jetson: detección YuNet] -> [Jetson: reconocimiento ONNX + SQLite]
                    |                              |
                    v                              v
        [Jetson: controlador P/deadband]   [nombre/"Unknown" + confianza]
                    |                              |
                    v                              v
        [move_delta por USB Serial] -> [ESP32: valida límites, mueve steppers]
                    |
                    v
        [frame anotado + evento] -> [FastAPI: MJPEG + WebSocket] -> [Dashboard React]
```

`vision/` corre en proceso dentro de `app/backend` (mismo proceso Python, hilo de
background) — no es un microservicio aparte. Ver justificación en `AGENTS.md` y en
el plan de arquitectura original.

## Flujo end-to-end

1. Frame capturado (`cv2.VideoCapture`, V4L2/GStreamer).
2. YuNet detecta rostro(s); se elige el de bbox más grande (MVP, sin multi-rostro).
3. Offset en píxeles vs. centro del frame → controlador P con deadband → delta
   pan/tilt.
4. Delta enviado como `move_delta` (ver `docs/protocol.md`) por USB Serial.
5. ESP32 valida límites suaves, mueve `AccelStepper`, responde telemetría.
6. El siguiente frame refleja la nueva orientación (retroalimentación de visual
   servoing — no hay encoder, el frame siguiente es la confirmación).
7. En paralelo, a cadencia reducida (cada 5-10 frames), el crop del rostro
   trackeado pasa por el modelo de embeddings + match coseno en SQLite.
8. El frame anotado se codifica a JPEG y queda en estado compartido → MJPEG.
9. El evento estructurado (bbox, nombre, confianza, telemetría) se empuja por
   WebSocket.

## Decisiones y alternativas descartadas

- **Detección: OpenCV YuNet** — descartado Haar cascades (impreciso), MTCNN (muy
  pesado en Nano), SSD-MobileNet genérico (innecesariamente grande).
- **Reconocimiento: modelo ONNX (`w600k_mbf.onnx` de InsightFace `buffalo_sc`) vía
  `onnxruntime`** — NO el paquete pip `insightface` (falla al compilar en
  Python 3.6/aarch64 de la Jetson Nano). Fallback documentado: `dlib`/
  `face_recognition` si el ONNX resulta impráctico de conseguir.
- **Almacenamiento: SQLite + numpy, sin vector DB** — a la escala de decenas de
  personas, un escaneo coseno por fuerza bruta es microsegundos. FAISS/Milvus
  serían sobre-ingeniería.
- **Control: P con deadband, no PID desde el día uno** — escalar solo si aparece
  offset estacionario u oscilación real en pruebas.

## Riesgos conocidos (ver detalle en el plan de arquitectura)

- JetPack 4.6 (Ubuntu 18.04 / Python 3.6 / CUDA 10.2) es EOL — instalar
  `onnxruntime` y un OpenCV con soporte DNN (`FaceDetectorYN` requiere OpenCV
  ≥4.5.4, y JetPack 4.6 trae 4.1.1) es una tarea real, tratarla como hito propio.
- Estabilidad del path serial (`/dev/ttyUSB0` puede cambiar) — mitigar con regla
  `udev` (ver `docs/hardware-wiring.md`).
- Rango mecánico del gimbal y velocidad de los steppers acotan el tuning del
  controlador — pendiente de medir con el hardware real.
