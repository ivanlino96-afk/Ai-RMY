# Spec: Detección y reconocimiento facial de personas registradas

## Contexto y objetivo

El sistema debe poder observar la cámara en vivo y responder a la pregunta "¿quién está
frente a la cámara?": distinguir entre personas ya registradas (mostrando su nombre) y
personas no registradas ("Desconocido"). Para lograrlo, el usuario debe poder dar de alta,
editar y eliminar personas conocidas, cada una identificada mediante 3 fotografías de su
rostro y datos personales básicos.

Esta funcionalidad es la base de cualquier comportamiento posterior del gimbal que dependa
de saber quién es la persona detectada (por ejemplo, seguimiento dirigido a alguien
específico).

## Usuarios

- **Usuario operador**: la única persona que interactúa con el sistema. Da de alta, edita
  y elimina personas conocidas, y observa la vista en vivo con las identificaciones. No
  existen distintos roles ni permisos diferenciados para esta funcionalidad.

## Historias de usuario

- Como usuario, quiero dar de alta a una persona conocida con su nombre, edad, correo
  electrónico, teléfono y 3 fotos de su rostro tomadas con la cámara, para que el sistema
  pueda reconocerla automáticamente en el futuro.
- Como usuario, quiero ver en la vista en vivo quién está frente a la cámara (nombre si es
  conocida, "Desconocido" si no), para saber en todo momento quién está presente.
- Como usuario, quiero editar los datos de una persona ya registrada, para corregir o
  actualizar su información cuando sea necesario, sin tener que rehacer todo si no cambié
  sus fotos.
- Como usuario, quiero eliminar a una persona registrada, para que el sistema deje de
  reconocerla y borre todos sus datos si ya no es relevante.
- Como usuario, quiero que el sistema me avise si intento registrar a alguien duplicado o
  si la cámara se desconecta, para no perder tiempo con un alta inconsistente o una falla
  de hardware sin darme cuenta.

## Requisitos funcionales

- **RF-1**: El sistema debe permitir dar de alta a una persona capturando exactamente 3
  fotografías de su rostro tomadas en el momento con la cámara. No se permite subir
  fotografías desde archivos existentes.
- **RF-2**: El sistema debe guiar al usuario para tomar las 3 fotografías en este orden: de
  frente, con el rostro ligeramente hacia la izquierda, y con el rostro ligeramente hacia
  la derecha. Durante la captura, el sistema debe detectar el rostro automáticamente en
  tiempo real y mostrar un encuadre visual sobre él, para ayudar al usuario a posicionarse
  correctamente antes de tomar cada foto.
- **RF-3**: El sistema debe requerir, además de las 3 fotos, el nombre, la edad, el correo
  electrónico y el número de teléfono de la persona como datos obligatorios del alta. No
  existe restricción de rango o validez sobre el valor de la edad. Estos datos se guardan
  como registro de la persona para uso en futuras implementaciones y estadísticas; esta
  funcionalidad no los utiliza para notificaciones ni ninguna otra acción por ahora.
- **RF-4**: El sistema debe rechazar cualquier fotografía de alta en la que no se detecte
  un rostro con claridad suficiente para procesarlo (incluyendo fotos de baja calidad o
  borrosas) o en la que se detecte más de un rostro, y pedir al usuario que vuelva a tomar
  esa fotografía.
- **RF-5**: El sistema debe validar que las 3 fotografías aceptadas correspondan al mismo
  rostro con al menos 90% de certeza (el mismo umbral usado para el reconocimiento en
  vivo), y rechazar el alta —pidiendo repetir las fotos— si no se alcanza ese nivel de
  consistencia.
- **RF-6**: Si el proceso de alta se abandona antes de completar las 3 fotos válidas y los
  datos obligatorios, el sistema debe descartar todo el registro parcial — no debe quedar
  una persona incompleta guardada.
- **RF-7**: Si el nombre o el teléfono ingresados en un alta coinciden con los de una
  persona ya registrada, el sistema debe notificar al usuario que esa persona ya existe.
  Una persona previamente eliminada no cuenta para esta verificación.
- **RF-8**: El sistema debe permitir editar los datos de una persona registrada. Las 3
  fotografías solo deben volver a subirse desde cero si el usuario decide editar
  específicamente las fotografías; el resto de los datos (nombre, edad, correo, teléfono)
  puede editarse de forma independiente sin afectar las fotos existentes. Si el usuario
  cancela la edición antes de completar la resubida de las 3 fotos, se descartan los
  cambios y se conservan los datos y fotos anteriores sin modificar.
- **RF-9**: El sistema debe permitir eliminar a una persona registrada, solicitando
  confirmación explícita antes de borrar de forma permanente todos sus datos (fotos, datos
  personales e información derivada para el reconocimiento). Si el usuario cancela la
  confirmación, no se elimina nada y la persona permanece sin cambios.
- **RF-10**: Si se elimina una persona mientras está siendo reconocida activamente en la
  vista en vivo, el sistema debe dejar de reconocerla a partir del siguiente cuadro
  procesado, sin comportamiento especial adicional.
- **RF-11**: Durante el uso en vivo, el sistema debe intentar detectar y reconocer todos
  los rostros presentes en cuadro simultáneamente, no solo uno principal.
- **RF-12**: Para cada rostro que coincida con una persona registrada con al menos 90% de
  certeza, el sistema debe mostrar un recuadro verde alrededor del rostro con el nombre de
  la persona.
- **RF-13**: Para cada rostro que no alcance 90% de certeza de coincidencia con ninguna
  persona registrada, el sistema debe mostrar un recuadro rojo con la etiqueta
  "Desconocido".
- **RF-14**: Si una persona reconocida sale de cuadro y vuelve a aparecer dentro de los 30
  segundos siguientes, el sistema debe conservar su identidad reconocida en lugar de
  tratarla como una detección nueva. Pasado ese tiempo, se reconoce de nuevo como una
  detección independiente.
- **RF-15**: Si no hay ninguna persona registrada en el sistema, todos los rostros
  detectados deben mostrarse como "Desconocido".
- **RF-16**: Si la cámara se desconecta durante el uso, el sistema debe notificar al
  usuario que la cámara está desconectada. Cada evento de desconexión y reconexión genera
  su propia notificación, sin límite de repeticiones.
- **RF-17**: El sistema debe validar el formato del correo electrónico y del teléfono
  ingresados, rechazando el formulario y solicitando su corrección si el formato no es
  válido.
- **RF-18**: Si, en un mismo rostro detectado, más de una persona registrada alcanzara 90%
  o más de certeza, el sistema debe asignar la coincidencia de mayor certeza entre ellas.
  Se asume que el proceso de alta (RF-5) hace que esta situación no debería ocurrir en
  condiciones normales.

## Criterios de aceptación (EARS)

- El sistema SHALL requerir exactamente 3 fotografías de rostro, tomadas con la cámara,
  para completar el alta de una persona.
- MIENTRAS el usuario esté tomando las 3 fotografías de alta, el sistema SHALL detectar el
  rostro en tiempo real y SHALL mostrar un encuadre visual sobre él.
- CUANDO el usuario tome una fotografía de alta sin un rostro detectable con claridad
  suficiente, o con más de un rostro detectable, el sistema SHALL rechazar esa fotografía y
  SHALL solicitar una nueva.
- CUANDO las 3 fotografías de un alta no alcancen 90% de certeza de correspondencia entre
  sí, el sistema SHALL rechazar el alta y SHALL solicitar que se repitan las fotos.
- SI el proceso de alta se interrumpe antes de completar las 3 fotos y los datos
  obligatorios, ENTONCES el sistema SHALL descartar cualquier dato parcial de esa persona.
- CUANDO el nombre o el teléfono de un alta nueva coincidan con los de una persona ya
  registrada (no eliminada), el sistema SHALL notificar al usuario que esa persona ya
  existe.
- CUANDO el usuario edite una persona sin modificar sus fotografías, el sistema SHALL
  permitir guardar los cambios sin solicitar nuevas fotos.
- CUANDO el usuario edite las fotografías de una persona, el sistema SHALL requerir que las
  3 fotografías se vuelvan a subir desde cero.
- SI el usuario cancela la edición de fotografías antes de completarla, ENTONCES el sistema
  SHALL conservar los datos y fotos previos sin cambios.
- CUANDO el usuario solicite eliminar una persona, el sistema SHALL pedir confirmación
  explícita antes de borrar todos sus datos de forma permanente.
- SI el usuario cancela la confirmación de borrado, ENTONCES el sistema SHALL no eliminar
  ningún dato.
- CUANDO una persona reconocida reaparezca en cuadro dentro de los 30 segundos posteriores
  a salir de él, el sistema SHALL mantener su identidad reconocida previa.
- CUANDO una persona reconocida reaparezca después de más de 30 segundos fuera de cuadro,
  el sistema SHALL evaluarla como una detección nueva.
- MIENTRAS el sistema esté en uso en vivo, el sistema SHALL evaluar cada rostro detectado
  en cuadro de forma independiente.
- CUANDO un rostro detectado alcance 90% o más de certeza de coincidencia con una persona
  registrada, el sistema SHALL mostrar un recuadro verde con el nombre de esa persona.
- CUANDO más de una persona registrada alcance 90% o más de certeza para el mismo rostro,
  el sistema SHALL asignar la coincidencia de mayor certeza.
- CUANDO un rostro detectado no alcance 90% de certeza con ninguna persona registrada, el
  sistema SHALL mostrar un recuadro rojo con la etiqueta "Desconocido".
- SI no hay personas registradas, ENTONCES el sistema SHALL mostrar todos los rostros
  detectados como "Desconocido".
- SI la cámara se desconecta, ENTONCES el sistema SHALL notificar al usuario de la
  desconexión.
- CUANDO el correo electrónico o el teléfono ingresados tengan un formato inválido, el
  sistema SHALL rechazar el formulario y SHALL solicitar su corrección.

## Requisitos no funcionales

- **RNF-1**: El tiempo entre la detección de un rostro y la asignación de su identidad
  (nombre o "Desconocido") no debe superar 1 segundo.
- **RNF-2**: El umbral mínimo de certeza para considerar una coincidencia positiva es 90%;
  por debajo de ese umbral, la persona se muestra como "Desconocido" — se prioriza evitar
  falsos positivos sobre evitar falsos negativos.
- **RNF-3**: No existe un límite máximo de personas que se puedan registrar en el sistema.
- **RNF-4**: Se asume un entorno con buena iluminación como condición normal de uso; el
  comportamiento bajo poca luz no es un requisito de esta versión.
- **RNF-5**: La determinación de la identidad de un rostro y su nivel de certeza debe
  tratarse como un resultado ya calculado; la presentación visual (color de recuadro,
  etiqueta) únicamente debe reflejar ese resultado, sin decidir ni recalcular identidad por
  su cuenta (alineado con el principio de "UI sin lógica" de `docs/constitution.md`).
- **RNF-6**: Todo criterio de aceptación de esta spec debe contar con al menos un caso de
  prueba automatizado que falle sin el comportamiento implementado y pase con él, antes de
  integrarse (alineado con el principio "sin test, no hay merge" de `docs/constitution.md`).
- **RNF-7**: Los datos personales capturados en el alta (edad, correo electrónico,
  teléfono), al igual que las fotografías, deben tratarse solo con almacenamiento local y
  nunca versionarse en el repositorio (alineado con el principio de datos locales de
  `docs/constitution.md`).

## Casos límite

- Fotografía de alta sin rostro detectable con claridad suficiente (incluye baja calidad o
  imagen borrosa), o con más de un rostro → se rechaza y se pide otra.
- Las 3 fotografías de un alta no alcanzan 90% de certeza de correspondencia entre sí → se
  rechaza el alta completo.
- Alta abandonada a la mitad (menos de 3 fotos válidas o datos incompletos) → se descarta
  todo, no queda registro parcial.
- Nombre o teléfono duplicado al dar de alta → se notifica al usuario, no se crea el
  registro automáticamente. Una persona previamente eliminada no cuenta para esta revisión.
- Edición de fotografías cancelada antes de completarse → se descartan los cambios, se
  conservan los datos y fotos anteriores.
- Confirmación de borrado cancelada → no se elimina ningún dato.
- Eliminación de una persona → borra permanentemente todos sus datos (fotos, datos
  personales e información derivada), no solo las fotos.
- Eliminación de una persona mientras está siendo reconocida en vivo → deja de reconocerse
  desde el siguiente cuadro, sin transición especial.
- No hay personas registradas todavía → todos los rostros se muestran como "Desconocido".
- Rostro con certeza de coincidencia por debajo del 90% → se muestra como "Desconocido"
  aunque exista una coincidencia parcial.
- Dos personas registradas superan el 90% de certeza para el mismo rostro (se asume un caso
  poco probable dado RF-5) → se asigna la de mayor certeza.
- Correo electrónico o teléfono con formato inválido → se rechaza el formulario y se
  solicita corregirlo.
- Persona registrada con lentes, gorra o cubrebocas → es aceptable que el sistema no la
  reconozca; no se considera una falla.
- Cámara desconectada o reconectada durante el uso → cada evento se notifica al usuario de
  forma independiente.

## Fuera de alcance

- Corrección manual en tiempo real de una identificación incorrecta por parte del usuario.
- Visualización de las 3 fotografías guardadas de una persona ya registrada desde la
  interfaz.
- Compensación automática o iluminación externa ante poca luz (posible mejora futura).
- Detección de suplantación (por ejemplo, un rostro mostrado en una foto o pantalla en
  lugar de una persona real presente frente a la cámara).
- Subida de fotografías desde archivos existentes para el alta (solo captura en vivo, ver
  RF-1).
- Campos adicionales de diferenciación entre personas más allá de nombre, edad, correo y
  teléfono (nombre y teléfono ya se usan para detectar altas duplicadas según RF-7; edad y
  correo son solo informativos).
- Cualquier decisión de plataforma de entrega distinta al dashboard web ya definido en
  `AGENTS.md` (esta funcionalidad no cambia esa decisión).

## Criterios de finalización

- El proceso de alta (primera configuración) de una persona debe ser lo suficientemente
  robusto para que, inmediatamente después de completarlo, esa persona sea reconocida con
  al menos 90% de certeza la primera vez que aparezca frente a la cámara.

## Dudas abiertas [NECESITA ACLARACIÓN]

Ninguna pendiente por el momento.
