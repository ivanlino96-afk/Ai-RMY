# Protocolo serial Jetson ↔ Arduino MKR Zero

Fuente única de verdad. `firmware/lib/SerialProtocol` y `vision/src/vision/serial_link`
deben implementar exactamente esto — cualquier cambio se hace aquí primero.

- Transporte: USB Serial, 115200 baudios.
- Formato: una línea de JSON por mensaje (NDJSON), terminada en `\n`.
- Todo mensaje incluye `"proto": 1`.

## Jetson → Arduino MKR Zero

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

## Arduino MKR Zero → Jetson

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

Si el Arduino MKR Zero no recibe un mensaje válido dentro del timeout configurado, debe
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
Arduino MKR Zero nunca confía en que el lado Jetson ya validó el rango.

## Configuración del conjunto validado

Límites por defecto: Pan 0–12000 pulsos y Tilt −1500–1500 pulsos, relativos
al origen vigente. Pan equivale a 360° y Tilt a aproximadamente ±55° según
la medición del operador. Se pueden editar los límites en Configuración.
El modo manual utiliza pulsos; el seguimiento utiliza grados estimados con
la escala independiente de cada eje. Home redefine el cero sin mover motores.

## Firmware temporal `uno_calibration`

Compilación exclusiva para calibración manual: rechaza `move_delta` y `goto`.
Añade `move_steps` con `pan_steps` y `tilt_steps` enteros obligatorios: solo
un eje por orden, de -2000 a +2000 pulsos, distinto de cero. Rechaza órdenes
mientras hay movimiento y destinos fuera de los límites de pasos configurados.
`home` detiene y pone ambos contadores a cero; `stop` conserva los contadores.
No elimina las protecciones: sustituye los límites angulares no calibrados
por límites de pulsos. Cada paso es un pulso STEP, no un paso completo del motor.
Telemetría añade `calibration` (bool), `pan_steps` y `tilt_steps` (enteros).
Los campos angulares usan la escala medida de la transmisión; siguen siendo
estimaciones relativas, no mediciones externas. Los contadores reflejan pulsos
emitidos, no movimiento medido. `move_steps` también se admite en firmware normal.

En `uno_calibration`, velocidad inicial 160 pulsos/s y aceleración 400 pulsos/s².
El firmware normal conserva su velocidad de 40 pasos/s.

## Velocidad por orden de movimiento

`move_delta`, `goto` y `move_steps` aceptan el par opcional
`pan_speed` / `tilt_speed`: enteros de 1 a 4000 pulsos STEP/s.
Si se incluye uno, ambos son obligatorios; fuera del rango, el firmware
rechaza toda la orden sin cambiar velocidad ni destino. Si se omiten,
conserva las velocidades actuales. Se aplican antes de iniciar el movimiento;
no cambian límites, watchdog ni parada.
El arranque en calibración usa 160 pulsos/s; firmware normal usa 40.
El host adjunta el perfil manual a jog, calibración y Center; el perfil
automático a seguimiento y escaneo. Configuración local persistente en
`vision/data/motor-speeds.json`, aplicable a partir de la siguiente orden.

## Aceleración configurable

Las órdenes de movimiento admiten además `pan_accel` y `tilt_accel`,
enteros entre 1 y 20000 pulsos STEP/s². Ambos son obligatorios si se incluye
uno; valores inválidos rechazan toda la orden antes de cambiar el movimiento.
Si se omiten, se conserva la aceleración vigente. Calibración arranca con
400 pulsos/s²; firmware normal conserva 40. El host mantiene perfiles manual
y automático independientes con velocidad y aceleración por eje.
Las configuraciones antiguas conservan sus velocidades; al migrar reciben
aceleración manual 400 y automática 40. Cada cambio se aplica a la siguiente orden.
Estos rangos son validaciones numéricas, no una garantía de velocidad física
alcanzable por el controlador o el mecanismo. Pulso STEP mínimo: 10 µs.
El host espera el ACK de `move_steps` (mismo seq) durante hasta 2 s. Si falta,
no reintenta automáticamente: la orden pudo ejecutarse. ACK significa aceptada,
no confirma giro físico. Los contadores siguen sin realimentación del motor.

### Límites configurables de calibración en pasos
`move_steps` acepta conjuntamente `pan_min`, `pan_max`, `tilt_min`, `tilt_max` enteros entre -200000 y 200000. Mínimo < máximo y ambos intervalos deben contener cero. Por defecto: Pan [0,12000], Tilt [-1500,1500]. Son posiciones relativas al origen vigente, no incrementos. El firmware rechaza íntegramente destinos fuera del intervalo (no recorta). Cada orden lleva los límites guardados por el host; al guardar no hay movimiento. El firmware normal usa el mismo intervalo en pasos para limitar destinos angulares. `home` y reiniciar redefinen cero y por tanto desplazan la referencia física de estos intervalos.

### Seguimiento con transmisión calibrada (2026-09-29)
Escala informada por el operador: Pan 12000 pasos por 360°; Tilt 1500 pasos por aproximadamente 55°. Los grados son estimaciones relativas al cero, nunca lectura de encoder. `pan_min`, `pan_max`, `tilt_min`, `tilt_max` también se aceptan en `move_delta` y `goto`; actualizan el intervalo de pasos usado para limitar el destino angular en el firmware. Sin campos se usan Pan [0,12000], Tilt [-1500,1500]. `move_steps` se admite también en firmware normal, con los mismos límites y exclusión de movimiento en curso. Firmware de calibración sigue rechazando órdenes angulares.

### Transporte y seguimiento
En Uno, RX UART usa 256 bytes para recibir órdenes NDJSON completas mientras
se transmite telemetría. La salida JSON se escribe directamente a Serial, sin
crear una segunda cadena dinámica en la SRAM de 2 KB. El cliente considera
desactualizada la conexión tras 4 s sin telemetría válida y no reintenta órdenes
de movimiento sin ACK.
El controlador visual usa ganancias Pan −30° y Tilt +25° por desplazamiento
normalizado, máximo 15° por corrección y zona muerta independiente del 5% en
cada eje. La velocidad configurada es un máximo; movimientos cortos pueden
no alcanzarla. La pérdida del rostro o su centrado detienen la corrección.
