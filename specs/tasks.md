# Tareas: Detección y reconocimiento facial de personas registradas

> Basado en `specs/spec.md` (RF-1 a RF-18) y `specs/plan.md` (arquitectura, módulos, modelo de
> datos, decisiones). Ordenadas por dependencia: cada tarea solo depende de tareas anteriores en
> esta lista. Cada tarea incluye "RF cubiertos" y un criterio "Hecho cuando:" verificable
> (alineado con el principio 4 de `docs/constitution.md` — sin test, no hay merge).

## Configuración y modelo de datos (base para todo lo demás)

- [x] **T1. Actualizar `vision/config.py` con los nuevos valores de umbral y ventana**
  Subir `RecognitionConfig.match_threshold` a 0.90, agregar
  `enrollment_consistency_threshold` (0.90) e `identity_memory_seconds` (30).
  **RF cubiertos**: RNF-1, RNF-2, RF-5, RF-12, RF-13, RF-14, RF-18.
  **Hecho cuando:** un test de configuración lee estos tres valores y falla si alguno no existe
  o no tiene el valor esperado; el resto de tareas de `vision/` los consume desde aquí, no con
  números sueltos.

- [x] **T2. Extender el esquema SQLite en `vision/storage/repository.py`**
  Agregar a `people` las columnas `age`, `email`, `phone` (NOT NULL); agregar a `embeddings` la
  columna `pose` (`front`/`left`/`right`).
  **RF cubiertos**: RF-2, RF-3.
  **Hecho cuando:** un test de esquema crea una base nueva, inserta una persona con las 4 columnas
  y un embedding con `pose`, y falla en la versión anterior del esquema (columnas inexistentes).

## Repositorio (depende de T1, T2)

- [x] **T3. CRUD de `age`/`email`/`phone` en `FaceRepository`**
  `add_person`/`update_person`/`get_person` leen y escriben los 3 campos nuevos.
  **RF cubiertos**: RF-3.
  **Hecho cuando:** un test crea una persona con age/email/phone y verifica que `get_person`
  devuelve exactamente esos valores; falla contra la firma actual de `add_person` (solo
  name/notes).

- [x] **T4. Verificación de duplicados por nombre o teléfono**
  Nuevo método `existe_duplicado(name, phone)` en el repositorio: normaliza (trim + minúsculas)
  el nombre, compara teléfono exacto, y excluye personas eliminadas.
  **RF cubiertos**: RF-7.
  **Hecho cuando:** un test registra una persona, verifica que un nombre/teléfono repetido (con
  espacios/mayúsculas distintas) se detecta como duplicado, y que una persona eliminada no cuenta
  para la comparación.

- [x] **T5. `find_all_matches` (todas las coincidencias ≥ umbral, no solo la mejor)**
  Nuevo método que devuelve la lista completa de personas con score ≥ `match_threshold` para un
  embedding dado, ordenada por score descendente.
  **RF cubiertos**: RF-11, RF-18.
  **Hecho cuando:** un test con 2 personas registradas cuyos embeddings ambos superan el umbral
  para un mismo vector de entrada verifica que se devuelven ambas y que la de mayor score queda
  primera; falla si solo se implementa `find_best_match` (una sola coincidencia).

- [x] **T6. Borrado permanente en cascada incluyendo archivos de fotos**
  Extender `delete_person` para borrar, además de las filas de `people`/`embeddings`, los archivos
  de foto en `photos_dir/<person_id>/`.
  **RF cubiertos**: RF-9.
  **Hecho cuando:** un test crea una persona con fotos en disco, la elimina, y verifica que no
  quedan ni filas en SQLite ni archivos en el directorio; falla contra la versión actual que solo
  borra filas.

## Captura guiada de alta (depende de T1, T4)

- [x] **T7. Sesión de alta en memoria con captura guiada de 3 fotos**
  En `vision/enroll.py`: sesión efímera (no persistida) que exige el orden de poses
  front→left→right, rechaza una foto sin exactamente un rostro detectable, y expone el encuadre
  en tiempo real durante la captura.
  **RF cubiertos**: RF-1, RF-2, RF-4, RF-6.
  **Hecho cuando:** un test simula una foto sin rostro (rechazada), una con 2 rostros (rechazada),
  una sesión abandonada antes de 3 fotos (no persiste nada), y una sesión completa en el orden
  correcto (acepta las 3).

- [x] **T8. Validación de consistencia cruzada entre las 3 fotos**
  Al finalizar la sesión, calcular similitud coseno entre cada par de las 3 fotos y rechazar el
  alta completa si alguna comparación cae por debajo de `enrollment_consistency_threshold`.
  **RF cubiertos**: RF-5.
  **Hecho cuando:** un test con 3 embeddings sintéticos coherentes entre sí pasa, y otro test con
  un embedding "distinto" entre los 3 (por debajo del umbral) rechaza el alta completa sin
  guardar nada.

## Reconocimiento en vivo (depende de T1, T5)

- [x] **T9. Reconocimiento de todos los rostros por frame**
  En `vision/pipeline.py`: reemplazar `target = detections[0]` por un bucle sobre todas las
  detecciones del frame, cada una evaluada de forma independiente contra `find_all_matches`.
  **RF cubiertos**: RF-11, RF-15.
  **Hecho cuando:** un test con un detector fake que devuelve 3 detecciones y un repositorio sin
  personas registradas verifica que el evento resultante trae 3 resultados, todos "Desconocido";
  falla contra la versión actual que solo procesa `detections[0]`.

- [x] **T10. Memoria de identidad de 30 segundos por rostro**
  Reemplazar `_LabelCache` (decaimiento por conteo de frames) por un registro por
  rostro/identidad con marca de tiempo, usando `identity_memory_seconds` de T1.
  **RF cubiertos**: RF-14.
  **Hecho cuando:** un test con reloj fake simula un rostro reconocido que desaparece y reaparece
  a los 10s (conserva identidad) y otro que reaparece a los 40s (se reevalúa como detección
  nueva).

- [x] **T11. Etiquetas y colores: "Desconocido"/rojo, nombre/verde**
  Reemplazar `UNKNOWN_LABEL = "Unknown"` por `"Desconocido"` y el color naranja `(0,165,255)` por
  rojo en `_annotate`, aplicado por cada rostro (no uno global).
  **RF cubiertos**: RF-12, RF-13.
  **Hecho cuando:** un test de anotación verifica recuadro verde + nombre para score ≥90% y
  recuadro rojo + "Desconocido" para score <90%, para múltiples rostros en el mismo frame.

- [x] **T12. Evento de conexión/desconexión de cámara**
  En el loop de `_run`, emitir un evento explícito solo en cada transición
  conectado↔desconectado (no uno por frame fallido).
  **RF cubiertos**: RF-16.
  **Hecho cuando:** un test con una cámara fake que alterna frame válido/`None` varias veces
  verifica que se publica exactamente un evento por transición, no uno por intento de lectura.

## API backend (depende de T2–T12)

- [x] **T13. `schemas.py`: campos nuevos y validación de formato**
  `PersonIn`/`PersonOut` con `age`/`email`/`phone`; validador de formato de correo y teléfono que
  rechaza el payload con mensaje claro si el formato no es válido.
  **RF cubiertos**: RF-3, RF-17.
  **Hecho cuando:** un test de esquema Pydantic rechaza un correo sin `@` y un teléfono con
  letras, y acepta valores válidos junto con una edad sin restricción de rango.

- [x] **T14. Endpoints de sesión de alta guiada**
  En `routers/people.py`: iniciar sesión, enviar foto de la pose actual (con encuadre en vivo),
  finalizar (valida consistencia + duplicados + formato, persiste) o cancelar (descarta).
  **RF cubiertos**: RF-1, RF-2, RF-4, RF-6.
  **Hecho cuando:** un test de integración (`TestClient`) completa un alta de extremo a extremo
  (3 fotos válidas + datos) y obtiene 201 con la persona creada; otro test cancela a mitad de
  camino y verifica que `GET /api/people` no la incluye.

- [x] **T15. Exponer verificación de duplicados en el endpoint de alta**
  Usar `existe_duplicado` (T4) antes de persistir; responder con un error claro y accionable si
  hay coincidencia por nombre o teléfono.
  **RF cubiertos**: RF-7.
  **Hecho cuando:** un test de integración da de alta a una persona, intenta repetir el alta con
  el mismo teléfono y variando el nombre, y recibe una respuesta de conflicto (no un 201 ni un
  500).

- [x] **T16. Edición: datos independientes de fotos, con cancelación**
  `PATCH` de datos (nombre/edad/correo/teléfono) sin exigir fotos; endpoint separado para
  re-captura de fotos que reutiliza el flujo de sesión guiada de T14 y no aplica cambios si se
  cancela antes de completar las 3 fotos.
  **RF cubiertos**: RF-8.
  **Hecho cuando:** un test edita solo el correo de una persona y verifica que sus fotos/
  embeddings no cambian; otro test inicia edición de fotos, cancela, y verifica que persisten los
  datos y embeddings previos.

- [x] **T17. Borrado con confirmación explícita**
  El endpoint de borrado exige un parámetro/flag de confirmación explícita; sin él, no borra
  nada y no cambia el estado de la persona.
  **RF cubiertos**: RF-9, RF-10.
  **Hecho cuando:** un test llama borrado sin confirmación (persona intacta), luego con
  confirmación (persona y sus fotos desaparecen); un test de pipeline verifica que, tras el
  borrado, el siguiente ciclo de reconocimiento ya no encuentra coincidencias para esa persona.

- [x] **T18. Evento WebSocket con lista de detecciones y estado de cámara**
  `routers/events.py`/el payload del evento pasan de una única detección a una lista, más el
  campo de conexión de cámara de T12.
  **RF cubiertos**: RF-11, RF-12, RF-13, RF-15, RF-16.
  **Hecho cuando:** un test de integración abre el WebSocket, fuerza un frame con 2 rostros
  (uno reconocido, uno no) y verifica que el evento recibido trae una lista con ambos resultados
  correctamente etiquetados.

## Frontend (depende de T13–T18; presentación pura, sin lógica de protocolo/visión)

- [ ] **T19. Flujo de captura guiada (encuadre en vivo + pasos + formulario)**
  Componente que consume los endpoints de T14: muestra el encuadre recibido del backend, guía
  las 3 poses en orden, y el formulario de nombre/edad/correo/teléfono.
  **RF cubiertos**: RF-1, RF-2, RF-3, RF-4, RF-5, RF-6, RF-17.
  **Hecho cuando:** probado manualmente en el navegador, el flujo completo de alta (3 fotos +
  datos) crea una persona visible en la lista; una foto rechazada por el backend muestra el
  mensaje de reintento sin avanzar de paso.

- [ ] **T20. Overlay de múltiples recuadros en la vista en vivo**
  `DetectionOverlay` dibuja un recuadro por cada detección del evento (verde/nombre o rojo/
  "Desconocido"), sin recalcular ni decidir nada — solo renderiza el arreglo recibido.
  **RF cubiertos**: RF-11, RF-12, RF-13, RF-14, RF-15.
  **Hecho cuando:** probado manualmente con 2+ personas frente a la cámara (una registrada, una
  no), ambos recuadros aparecen simultáneamente con el color/etiqueta correctos.

- [ ] **T21. Edición, borrado con confirmación, y notificaciones de duplicado/cámara**
  UI de edición (datos vs. fotos, con opción de cancelar), diálogo de confirmación de borrado, y
  notificaciones para duplicado (T15) y conexión/desconexión de cámara (T12/T18).
  **RF cubiertos**: RF-7, RF-8, RF-9, RF-10, RF-16.
  **Hecho cuando:** probado manualmente: cancelar un borrado no elimina a la persona; confirmar
  sí; desconectar la cámara física dispara una notificación visible sin recargar la página.

## Verificación final (depende de todas las anteriores)

- [ ] **T22. Verificación end-to-end del criterio de finalización**
  Con el sistema completo corriendo, dar de alta a una persona nueva y confirmar que es
  reconocida con ≥90% de certeza la primera vez que aparece frente a la cámara tras el alta.
  **RF cubiertos**: RF-1 a RF-18 (criterio de finalización de `spec.md`).
  **Hecho cuando:** toda la suite de pruebas automatizadas de T1–T18 pasa en verde, y la
  verificación manual de T19–T21 se completó sin hallazgos pendientes.
