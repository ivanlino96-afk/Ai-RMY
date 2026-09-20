# Wiring de hardware — Ai-RMY

Este documento se completa a medida que se define el hardware físico exacto. No
asumir pinout desde el orden de cableado — validar aquí y en calibración.

## Pendiente de definir (bloquea detalle de wiring)

- [ ] Modelo exacto de la dev board ESP32 (afecta pines disponibles/reservados).
- [ ] Modelo/tamaño de los 2 motores a pasos (NEMA 17 / 23, corriente nominal).
- [ ] Configuración de microstepping de los drivers TB660 (DIP switches).
- [ ] Especificación de la fuente externa para los motores (voltaje/corriente).
- [ ] Modelo de cámara conectada a la Jetson (CSI vs. USB, resolución, FOV).

## Reglas fijas (no cambian con el hardware específico)

- Los motores se alimentan de una fuente externa dedicada, dimensionada según el
  driver TB660 y el motor elegido. **Nunca** desde el riel 5V/USB del ESP32.
- Masa común obligatoria entre la fuente de motores, los drivers TB660 y el ESP32.
- Conexión Jetson↔ESP32: USB Serial (mismo cable de datos, no alimentación cruzada
  si el ESP32 tiene su propia fuente).

## Pinout ESP32 (pendiente)

| Señal | Pin ESP32 | Nota |
| --- | --- | --- |
| STEP (pan) | TBD | |
| DIR (pan) | TBD | |
| STEP (tilt) | TBD | |
| DIR (tilt) | TBD | |
| ENABLE (ambos drivers, si aplica) | TBD | |

## Regla udev en la Jetson (path serial estable)

El path `/dev/ttyUSB0`/`/dev/ttyACM0` no está garantizado entre reinicios o
reconexiones. Crear una regla udev que mapee el ESP32 por vendor/product ID (y
número de serie si el chip USB-UART lo expone) a un symlink estable, ej.
`/dev/gimbal`. Pendiente: identificar el chip USB-UART real de la dev board
elegida (CP2102, CH340, o USB nativo del ESP32-S2/S3) para escribir la regla
exacta — ver `scripts/provision_jetson.sh`.
