# Plan técnico: Detección y reconocimiento facial de personas registradas

> Documento de diseño (HOW). No contiene código — únicamente arquitectura, modelo de datos,
> pseudocódigo, decisiones y estrategia de pruebas. Implementa `specs/spec.md` sobre la base de
> código ya existente en `vision/` y `app/backend/` (ver `docs/architecture.md` para el contexto
> de arquitectura general del proyecto, que este plan extiende sin contradecir).

## 1. Arquitectura general

La funcionalidad se integra en el pipeline en proceso ya existente (`vision.Pipeline` +
`app/backend`), sin nuevos servicios ni procesos. Se agregan dos flujos sobre la arquitectura
actual:

```
                 ┌────────────────────────────────────────────┐
                 │              Alta / edición                 │
                 │  (sesión de captura guiada, no persiste     │
                 │   nada hasta finalizar con éxito)           │
                 └───────────────┬──────────────────────────────┘
                                 │ 3 fotos válidas + datos + consistencia ≥90%
                                 ▼
                        FaceRepository (SQLite)
                                 ▲
                                 │ lee personas/embeddings en cada ciclo
                 ┌───────────────┴──────────────────────────────┐
                 │           Pipeline (hilo de background)      │
                 │  cámara → YuNet (todas las detecciones)      │
                 │        → embedding + match por cada rostro   │
                 │        → color/etiqueta por rostro           │
                 │        → frame anotado (MJPEG) + evento (WS) │
                 └────────────────────────────────────────────────┘
```

El alta/edición y el reconocimiento en vivo comparten los mismos componentes de detección
(`YuNetDetector`) y de embedding (`FaceEmbedder`) — una sola instancia de cada uno, sin una
segunda librería de visión para el flujo de captura guiada (principio 1 de la constitución).

El reconocimiento en vivo pasa de "un rostro trackeado" a "todos los rostros en cuadro,
evaluados de forma independiente" (RF-11), y el resultado ya calculado (nombre/color) llega al
frontend como datos planos en el evento WebSocket — la UI solo dibuja, nunca decide (RNF-5,
principio 3).

**RF cubiertos**: RF-1, RF-2, RF-11, RF-12, RF-13, RF-15, RF-16.

## 2. Estructura de módulos

Se listan solo los módulos nuevos o modificados; el resto de `vision/` y `app/backend/` se
mantiene igual.

```
vision/src/vision/
├── enroll.py               # MODIFICADO: pasa de "un embedding desde una foto" a una
│                           #   sesión de alta con 3 fotos, validación de consistencia
│                           #   cruzada y estado descartable
├── detection/yunet.py      # SIN CAMBIOS: ya expone detect() -> lista de N detecciones;
│                           #   la captura guiada y el reconocimiento en vivo lo reutilizan
├── recognition/embedder.py # SIN CAMBIOS en la lógica de embedding; cambia el valor de
│                           #   configuración match_threshold (ver Modelo de datos/config)
├── storage/repository.py   # MODIFICADO: columnas nuevas en `people`, validación de
│                           #   duplicados, borrado en cascada incluyendo archivos de foto
├── pipeline.py              # MODIFICADO: itera TODAS las detecciones (no solo detections[0]),
│                           #   reemplaza _LabelCache (por conteo de frames) por un registro
│                           #   por identidad con ventana de 30s, cambia color naranja→rojo
│                           #   y etiqueta "Unknown"→"Desconocido", emite evento de
│                           #   cámara conectada/desconectada
└── config.py                # MODIFICADO: nuevos valores (match_threshold=0.90,
                            #   enrollment_consistency_threshold=0.90, identity_memory_seconds=30)

app/backend/
├── schemas.py                # MODIFICADO: PersonIn/PersonOut con age/email/phone;
│                             #   EnrollmentSessionOut para el flujo guiado de 3 fotos
├── routers/people.py         # MODIFICADO: endpoints de sesión de alta (iniciar, enviar foto
│                             #   guiada N, finalizar/cancelar), validación de duplicados,
│                             #   edición parcial vs. edición de fotos, confirmación de borrado
└── routers/events.py         # SIN CAMBIOS estructurales: el evento ya viaja por el mismo
                              #   WebSocket; ahora incluye una lista de detecciones en vez de una
```

En el frontend (`app/frontend/`) se añaden componentes de presentación pura para la sesión de
alta guiada (encuadre en vivo, indicador de paso 1/2/3, formulario de datos) y para mostrar
múltiples recuadros por frame; ninguno importa lógica de protocolo, visión o control (principio
3) — reciben únicamente el evento ya calculado.

**RF cubiertos**: RF-1, RF-2, RF-3, RF-4, RF-5, RF-6, RF-7, RF-8, RF-9, RF-11, RF-12, RF-13,
RF-14, RF-16, RF-17.

## 3. Modelo de datos

Extiende el esquema SQLite ya existente en `FaceRepository` (`vision/data/faces.db`, gitignored
— principio 5 / RNF-7). No se introduce una base de datos nueva ni un vector store (ver
Alternativas descartadas).

```
people
├── id            INTEGER PRIMARY KEY
├── name          TEXT NOT NULL
├── age           INTEGER NOT NULL          -- nuevo; sin validación de rango (RF-3)
├── email         TEXT NOT NULL             -- nuevo; formato validado en la capa de API (RF-17)
├── phone         TEXT NOT NULL             -- nuevo; formato validado en la capa de API (RF-17)
├── notes         TEXT                      -- se conserva, sin uso obligatorio
├── deleted_at    TEXT NULL                 -- nuevo; borrado permanente real (ver más abajo),
│                                           --   NO es soft-delete: se usa solo como marca
│                                           --   transitoria durante la transacción de borrado
└── created_at    TEXT NOT NULL

embeddings
├── id            INTEGER PRIMARY KEY
├── person_id     INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE
├── vector        BLOB NOT NULL              -- sin cambios (float32, comparado por coseno)
├── photo_path    TEXT NOT NULL
├── pose          TEXT NOT NULL              -- nuevo: 'front' | 'left' | 'right' (RF-2), para
│                                           --   poder exigir exactamente las 3 poses al alta
└── created_at    TEXT NOT NULL
```

**Índice de duplicados (RF-7)**: no se usa una restricción `UNIQUE` de SQL sobre
`(name, phone)` (ver Alternativas descartadas). La verificación de duplicados se hace en la capa
de aplicación con una consulta `WHERE deleted_at IS NULL AND (lower(trim(name)) = ? OR phone = ?)`
antes de insertar, para poder normalizar (espacios, mayúsculas) y excluir personas eliminadas
(RF-7 lo exige explícitamente).

**Borrado permanente (RF-9)**: `delete_person` ya elimina en cascada los `embeddings` vía FK;
se extiende para además borrar los archivos de foto en `photos_dir/<person_id>/` del disco en la
misma operación — hoy el código solo borra filas de SQLite y deja fotos huérfanas, lo cual viola
"borra todos sus datos" (RF-9). No se usa `deleted_at` como estado persistente; es una bandera
interna de la transacción de borrado (por si el borrado de archivos falla a mitad de camino, se
puede reintentar sin dejar el registro en un estado ambiguo), no un mecanismo de soft-delete de
cara al resto del sistema.

**Sesión de alta (RF-1, RF-6)**: la sesión de captura guiada (3 fotos + datos) vive **solo en
memoria** (en el proceso del backend, asociada a un `session_id` efímero) hasta que se completa
con éxito; recién ahí se escribe la fila de `people` + las 3 filas de `embeddings` en una sola
transacción. Si se abandona o cancela, no hay nada que limpiar en la base de datos porque nunca
se escribió (satisface RF-6 sin necesidad de un mecanismo de limpieza de registros parciales).

**Memoria de identidad de 30s (RF-14)**: es estado de ejecución del `Pipeline`, no un dato de
negocio — vive en memoria del proceso (estructura por rostro-en-seguimiento con marca de tiempo
de última vez visto), nunca se persiste en SQLite (ver Alternativas descartadas).

**RF cubiertos**: RF-1, RF-2, RF-3, RF-6, RF-7, RF-9, RF-14, RNF-7.

## 4. Diagramas o pseudocódigo

### 4.1 Sesión de alta guiada (RF-1, RF-2, RF-4, RF-5, RF-6)

```
iniciar_sesion_alta():
    session = { fotos: [], pose_esperada: 'front' }
    devolver session_id

# se repite 3 veces, una por pose, en orden estricto front -> left -> right
en_vivo_durante_captura(session_id, frame):
    detecciones = detector.detect(frame)
    si len(detecciones) == 0:
        devolver { encuadre: null }              # nada que dibujar todavía
    si no:
        devolver { encuadre: detecciones[0].bbox } # guía visual en tiempo real (RF-2)

capturar_foto(session_id, frame):
    detecciones = detector.detect(frame)
    si len(detecciones) != 1:
        rechazar("se requiere exactamente un rostro detectable con claridad")  # RF-4
        devolver
    embedding = embedder.embed_from_landmarks(frame, detecciones[0].landmarks)
    session.fotos.agregar({ pose: session.pose_esperada, embedding, frame })
    session.pose_esperada = siguiente_pose(session.pose_esperada)

finalizar_alta(session_id, datos_persona):
    si len(session.fotos) != 3:
        rechazar("alta incompleta")            # RF-6, no se guarda nada
        devolver
    # RF-5: las 3 fotos deben corresponder a la misma persona
    para cada par (a, b) en combinaciones(session.fotos, 2):
        si similitud_coseno(a.embedding, b.embedding) < 0.90:
            rechazar("las fotos no son consistentes entre sí, repetir alta")
            devolver
    # RF-7: duplicado por nombre o teléfono (excluye eliminados)
    si repository.existe_duplicado(datos_persona.name, datos_persona.phone):
        notificar("ya existe una persona con ese nombre o teléfono")
        devolver
    # RF-17: formato de correo/teléfono
    si no es_email_valido(datos_persona.email) o no es_telefono_valido(datos_persona.phone):
        rechazar("formato de correo o teléfono inválido")
        devolver
    # todo válido: única escritura transaccional
    person_id = repository.add_person(datos_persona + 3 embeddings con pose)
    descartar session de memoria
```

### 4.2 Reconocimiento en vivo multi-rostro (RF-11 a RF-15, RF-18, RNF-1, RNF-2)

```
por cada frame del pipeline:
    detecciones = detector.detect(frame)          # todas, no solo la más grande
    resultados = []
    para cada d en detecciones:
        identidad_recordada = memoria_identidad.buscar(d, ventana_segundos=30)  # RF-14
        si identidad_recordada is not None:
            resultados.agregar(identidad_recordada)
            continuar
        embedding = embedder.embed_from_landmarks(frame, d.landmarks)
        candidatos = repository.find_all_matches(embedding, umbral=0.90)  # todas las
                                                                            # personas ≥90%
        si candidatos está vacío:                  # incluye "no hay personas registradas" (RF-15)
            resultado = { label: "Desconocido", color: ROJO }             # RF-13
        si no:
            mejor = max(candidatos, clave=score)    # RF-18: mayor certeza gana
            resultado = { label: mejor.name, color: VERDE }               # RF-12
            memoria_identidad.recordar(d, mejor, ahora())
        resultados.agregar(resultado)

    evento = { detecciones: resultados, ... }       # cada rostro evaluado de forma
    publicar(frame_anotado_con(resultados), evento) #   independiente (EARS, RF-11)
```

`memoria_identidad` asocia una detección "nueva" con una identidad reciente por cercanía
espacial/temporal simple (posición del bbox en el frame anterior + tiempo transcurrido < 30s);
si el rostro no reaparece dentro de la ventana, se evalúa como detección nueva (RF-14, segunda
mitad del criterio EARS).

### 4.3 Edición (RF-8) y borrado (RF-9, RF-10)

```
editar_persona(person_id, cambios, nuevas_fotos=None):
    si nuevas_fotos is None:
        repository.update_person(person_id, cambios)   # nombre/edad/correo/teléfono, fotos intactas
        devolver
    # el usuario decidió editar fotos: exige el mismo flujo de alta guiada (3 fotos, RF-5, RF-4)
    session = iniciar_sesion_alta()
    ... captura guiada de 3 fotos nuevas ...
    si se cancela antes de completar:
        descartar session                              # datos y fotos anteriores intactos (RF-8)
        devolver
    repository.reemplazar_embeddings(person_id, session.fotos)
    repository.update_person(person_id, cambios)

eliminar_persona(person_id, confirmado):
    si no confirmado:
        devolver                                       # no se borra nada (RF-9)
    repository.delete_person(person_id)                # borra fila + embeddings (cascade) +
                                                        #   archivos de fotos en disco
    # el siguiente ciclo del pipeline ya no encuentra a person_id en find_all_matches:
    # deja de reconocerse "desde el siguiente cuadro" sin lógica especial adicional (RF-10)
```

### 4.4 Notificación de cámara (RF-16)

```
estado_camara_anterior = conectada

por cada intento de leer un frame:
    frame = camera.read()
    si frame is None:
        si estado_camara_anterior == conectada:
            emitir_evento(camara_conectada=False)    # una notificación por transición, no por frame
            estado_camara_anterior = desconectada
        continuar
    si estado_camara_anterior == desconectada:
        emitir_evento(camara_conectada=True)
        estado_camara_anterior = conectada
    ... procesar frame normalmente ...
```

**RF cubiertos**: RF-1, RF-2, RF-4, RF-5, RF-6, RF-7, RF-8, RF-9, RF-10, RF-11, RF-12, RF-13,
RF-14, RF-15, RF-16, RF-17, RF-18.

## 5. Decisiones técnicas justificadas

- **Reconocer todas las detecciones por frame, no solo `detections[0]`** (RF-11): `YuNetDetector.
  detect()` ya devuelve la lista completa ordenada por área; el cambio es de bucle, no de
  detector. Para respetar RNF-1 (≤1s de identidad) con varios rostros, el embedding sigue
  corriendo a la cadencia reducida existente (`run_every_n_frames`) pero ahora una vez por rostro
  detectado en ese ciclo — el costo escala con el número de rostros en cuadro, que en la práctica
  de este producto (una habitación, no una multitud) es bajo.
- **Subir el umbral de coincidencia de 0.45 (valor actual en `RecognitionConfig.
  match_threshold`) a 0.90**: es un cambio de configuración explícito exigido por RNF-2 y RF-12/
  RF-13/RF-18. Se prioriza evitar falsos positivos, tal como pide el RNF-2 — un valor conservador
  es coherente con la decisión ya documentada en `docs/architecture.md` de preferir "Desconocido"
  antes que una identificación incorrecta.
- **Reutilizar el mismo umbral (0.90) y el mismo cálculo de similitud coseno para la consistencia
  entre las 3 fotos de alta (RF-5)**: evita introducir una segunda métrica o un segundo umbral
  sin justificación — coherente con el principio 1 (stack mínimo) y con el criterio de
  finalización de la spec (reconocimiento ≥90% desde la primera aparición).
- **Guía visual en tiempo real durante la captura (RF-2) reutilizando `YuNetDetector`**: el mismo
  detector que ya corre en el pipeline de reconocimiento se usa para dibujar el encuadre en vivo
  durante el alta; no se evalúa una librería de detección en el navegador (ver Alternativas
  descartadas).
- **Verificación de duplicados en la capa de aplicación (repositorio), no como restricción SQL
  `UNIQUE`**: RF-7 exige normalizar el nombre (espacios/mayúsculas) y excluir personas eliminadas
  — ambas cosas requieren lógica de consulta, no un índice único plano. Además, permite devolver
  un mensaje claro al usuario en vez de un error de integridad de base de datos.
- **Memoria de 30 segundos como estado en memoria del `Pipeline`, no en SQLite** (RF-14): es un
  dato de sesión de uso en vivo, no un registro de negocio; persistirlo no aporta valor (se
  reinicia con cada arranque del pipeline de forma aceptable) y evita una tabla adicional solo
  para estado transitorio.
- **Borrado de archivos de fotos como parte de `delete_person`, en la misma operación que el
  borrado de filas**: hoy el código borra filas vía cascada de FK pero no toca el filesystem —
  se corrige para que RF-9 ("borra permanentemente todos sus datos") sea literalmente cierto,
  incluyendo las fotos en disco.
- **Sesión de alta en memoria de proceso, no en una tabla "personas incompletas"**: la forma más
  simple de garantizar RF-6 (nada de datos parciales) es no escribir nada hasta que la validación
  completa (3 fotos + consistencia + duplicados + formato) pasa; una tabla intermedia solo
  agregaría un estado a limpiar y una fuente más de inconsistencia.
- **Etiqueta "Desconocido" y color rojo reemplazan a "Unknown"/naranja en `pipeline.py`**: ajuste
  directo a RF-13 y al principio 6 de la constitución (idioma fijo — trato con el usuario en
  español); es un cambio de constante/color, no de lógica de reconocimiento.
- **`find_best_match` ya implementa "mayor certeza gana" (RF-18)**: se extiende a
  `find_all_matches` (todas las personas ≥90%, no solo la mejor) porque ahora se necesita saber
  si hay más de un candidato por encima del umbral para poder aplicar el desempate explícitamente
  documentado en RF-18, en vez de asumir implícitamente que nunca ocurre.

**RF cubiertos**: RF-2, RF-5, RF-6, RF-7, RF-9, RF-11, RF-12, RF-13, RF-14, RF-18, RNF-1, RNF-2.

## 6. Alternativas descartadas

- **Índice de base de datos (FAISS/Milvus) para el match multi-rostro**: descartado, igual que ya
  documenta `docs/architecture.md` — a la escala de "decenas de personas" un escaneo coseno con
  numpy por cada rostro detectado sigue siendo del orden de microsegundos; introducirlo violaría
  el principio 1 (stack mínimo) sin beneficio medible.
- **Restricción `UNIQUE` de SQL sobre `(name, phone)` para detectar duplicados**: descartada
  porque no permite normalizar el nombre ni excluir personas eliminadas sin lógica adicional de
  todas formas, y un error de integridad de SQLite no es un mensaje apto para mostrar al usuario
  (RF-7 pide una notificación explícita, no un error de base de datos).
- **Persistir la ventana de 30 segundos de "recordar identidad" en SQLite**: descartada — es
  estado efímero de una sesión de uso en vivo, no un registro de negocio; persistirlo agregaría
  una tabla y lógica de expiración sin aportar valor tras un reinicio del proceso.
- **Detector de rostro en el navegador (JS/WASM) para dibujar el encuadre en vivo durante la
  captura de alta**: descartado — implicaría una segunda librería de detección facial además de
  YuNet ya usada en el backend, violando el principio 1. En su lugar, la guía visual se calcula
  en el mismo pipeline de visión y se transmite al frontend igual que ya se hace con el frame
  anotado del reconocimiento en vivo.
- **Microservicio separado para el flujo de alta/edición**: descartado — ya establecido en
  `docs/architecture.md` que `vision` y `app/backend` viven en el mismo proceso; separar el alta
  en otro servicio rompería esa decisión sin necesidad, dado que el alta también depende del
  mismo detector/embedder en memoria.
- **Escalar el control de tracking a PID para compensar el costo extra de reconocer múltiples
  rostros por frame**: descartado — no hay evidencia de oscilación o de que el tracking (que
  sigue basándose en un único objetivo, el rostro más grande, sin cambios por esta funcionalidad)
  se vea afectado; está fuera del alcance de esta spec.
- **Tabla intermedia de "altas incompletas" para poder recuperar una sesión interrumpida**:
  descartada — RF-6 pide explícitamente descartar todo, no recuperar; agregar recuperación sería
  una funcionalidad no solicitada (no sobre-diseñar).

**RF cubiertos**: RF-6, RF-7, RF-11, RF-14, RF-18.

## 7. Estrategia de pruebas

Alineado con el principio 4 de la constitución y RNF-6: cada criterio de aceptación EARS de
`spec.md` debe tener al menos un caso de prueba automatizado que falle sin el comportamiento y
pase con él, antes de integrarse. Los componentes de visión (`detector`, `embedder`) se inyectan
por configuración/constructor (ya es el patrón actual de `enroll.py`/`pipeline.py`), por lo que
las pruebas pueden usar dobles/fakes en vez de depender de cv2/onnxruntime reales.

**Vision (`vision/tests/`)**:
- `test_enroll_session.py`: rechaza foto sin rostro o con >1 rostro (RF-4); rechaza si las 3
  fotos no superan 90% de consistencia entre sí (RF-5); descarta la sesión si se abandona antes
  de 3 fotos + datos completos (RF-6); exige orden de poses front→left→right (RF-2).
- `test_repository.py` (extiende el existente): detecta duplicado por nombre o teléfono
  normalizado, ignora eliminados (RF-7); `delete_person` borra filas Y archivos de fotos del
  disco (RF-9); `find_all_matches` devuelve todos los candidatos ≥90% y permite verificar que se
  elige el de mayor score (RF-18); age/email/phone se guardan y se leen correctamente (RF-3).
- `test_pipeline_multi_face.py`: con un detector fake que devuelve N detecciones y un embedder
  fake con vectores conocidos, verifica que cada rostro se evalúa de forma independiente (RF-11);
  colores/etiquetas correctos por encima/debajo de 90% (RF-12, RF-13); sin personas registradas,
  todos "Desconocido" (RF-15); un rostro que desaparece y reaparece antes de 30s conserva
  identidad, después de 30s se reevalúa como nuevo (RF-14, con un reloj fake inyectado).
- `test_pipeline_camera_events.py`: con una cámara fake que alterna entre frames válidos y `None`,
  verifica que se emite exactamente un evento por transición de conectado↔desconectado, no uno
  por frame (RF-16).

**Backend (`app/backend/tests/`, FastAPI `TestClient`)**:
- Alta: foto inválida → 422 (RF-4); duplicado → conflicto explícito con mensaje (RF-7); correo o
  teléfono con formato inválido → rechazo con mensaje de corrección (RF-17); alta exitosa
  persiste name/age/email/phone + 3 embeddings (RF-1, RF-3).
- Edición: cambiar solo nombre/edad/correo/teléfono no exige fotos (RF-8, primera mitad); iniciar
  edición de fotos y cancelar antes de completarla conserva los datos/fotos previos (RF-8,
  segunda mitad).
- Borrado: requiere confirmación explícita en la petición; cancelar no borra nada; confirmar
  borra persona + embeddings + fotos (RF-9); una persona borrada deja de aparecer en
  `find_all_matches` en la siguiente consulta, verificando indirectamente RF-10 a nivel de
  repositorio ya que el pipeline no mantiene estado propio de "personas activas".

**Fuera de esta estrategia**: no se requieren cambios ni pruebas de firmware (esta funcionalidad
no modifica `docs/protocol.md` ni el control de motores); no se requieren pruebas físicas con
motores.

**RF cubiertos**: RF-1 a RF-18 (cobertura completa vía RNF-6).

---

## Cobertura total de requisitos funcionales

Todos los RF de `spec.md` quedan cubiertos por al menos una sección de este plan:

RF-1 (§1, §2, §4.1) · RF-2 (§1, §2, §4.1, §5) · RF-3 (§2, §3, §4.1) · RF-4 (§2, §4.1, §7) ·
RF-5 (§3, §4.1, §5, §7) · RF-6 (§3, §4.1, §6, §7) · RF-7 (§3, §4.1, §5, §6, §7) ·
RF-8 (§2, §4.3, §7) · RF-9 (§3, §4.3, §5, §7) · RF-10 (§4.3, §7) · RF-11 (§1, §2, §4.2, §5, §6, §7) ·
RF-12 (§1, §4.2, §5, §7) · RF-13 (§1, §4.2, §5, §7) · RF-14 (§3, §4.2, §5, §6, §7) ·
RF-15 (§1, §4.2, §7) · RF-16 (§1, §2, §4.4) · RF-17 (§2, §4.1, §7) · RF-18 (§4.2, §5, §6, §7).

Este plan respeta los 6 principios de `docs/constitution.md`: stack mínimo (§5, §6), spec antes
que código (este documento se genera antes de tocar código), UI sin lógica (§1, §2), sin test no
hay merge (§7), datos locales nunca versionados (§3), e idioma fijo (todo el documento en
español; los nombres de módulos/campos citados usan inglés, como ya exige el código existente).
