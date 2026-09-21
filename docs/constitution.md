# Constitución del Proyecto

1. **Stack mínimo**: una sola librería por responsabilidad y capa; añadir una segunda exige retirar la anterior en el mismo PR.
2. **Spec antes que código**: ningún cambio de protocolo/API se escribe sin antes actualizar el `.md` correspondiente en `docs/`.
3. **UI sin lógica**: los componentes de presentación no importan módulos de protocolo, visión ni control; solo reciben datos ya procesados.
4. **Sin test, no hay merge**: todo módulo de parsing, límites o control requiere un test que falle sin el cambio y pase con él.
5. **Datos locales, nunca versionados**: biometría, modelos y credenciales solo viven en almacenamiento local gitignorado (SQLite/archivos), jamás en el repo.
6. **Idioma fijo**: código, identificadores y mensajes de commit en inglés; documentación y trato con el usuario en español.
