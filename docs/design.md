# Sistema de diseño Ai-RMY

Fuente de verdad de la identidad visual de la app (dashboard web y, a
partir de aquí, la app móvil Flutter). Estética "spec-sheet" técnico
militar: fondo casi negro, un único acento de marca, semáforo de estado
funcional separado del acento, tipografía condensada en mayúsculas para
todo lo estructural y monoespaciada para datos/cuerpo.

Extraído directamente de `app/frontend/src/styles/index.css` y de los
componentes en `app/frontend/src/components/hud/`. Si este documento y el
CSS alguna vez difieren, el CSS manda — actualizar este archivo.

## Paleta

| Token | Hex | Uso |
|---|---|---|
| `void` | `#0a0a0a` | Fondo de página (`body`). |
| `panel` | `#141414` | Fondo de panel/card (`CornerBracketPanel`). |
| `hairline` | `#242424` | Todos los bordes 1px por defecto. |
| `ink` | `#fafafa` | Texto principal. |
| `ink-dim` | `#8a8a8a` | Texto secundario, `field-label`, placeholders. |
| `accent` | `#ff8c00` | **Solo marca/interacción**: nav activo, CTA, chip de código `SYS-0N`, toggle seleccionado. Nunca semáforo de estado. |
| `lock` | `#00c758` | Estado OK/conectado/bloqueado-en-objetivo. |
| `warn` | `#edb200` | Estado de precaución/bloqueante-no-crítico. |
| `alert` | `#e40014` | Estado de error/desconectado/peligro. |

**Regla no negociable:** el estado (`lock`/`warn`/`alert`) nunca se
expresa solo con color — siempre va acompañado de texto explícito (ver
`StatusBadge`). El acento (`accent`) nunca se usa para señalar estado;
está reservado a interacción/marca.

## Tipografía

Dos familias, sin una tercera para nada:

- **Barlow Condensed** (500/600/700) — headings (`h1,h2,h3`), botones,
  labels de campo (`.field-label`), eyebrows de `PageHeader`. Siempre en
  mayúsculas con tracking ancho (`tracking-[0.04em]` a `0.14em` según el
  elemento).
- **IBM Plex Mono** (400/500/600/700) — fuente por defecto de `body`
  (todo el texto corrido y datos es monoespaciado por diseño: refuerza el
  look de "instrumento técnico"). Números tabulares (`.tabular`,
  `font-variant-numeric: tabular-nums`) en cualquier lectura numérica
  (ángulos, contadores, timestamps).

Google Fonts, cargadas en `index.html`:
```
Barlow+Condensed:wght@500;600;700
IBM+Plex+Mono:wght@400;500;600;700
```

Utilidad `.text-readout`: números grandes de instrumento
(`clamp(32px, 4.5vw, 65px)`, `letter-spacing: -0.03em`, tabular).

## Forma

- **Sin `border-radius` en ningún lugar** — esquinas siempre rectas.
- Bordes hairline de 1px (`hairline #242424`) como separador por defecto.
- Decoración de esquina: 4 corchetes en L de 14×14px (`h-3.5 w-3.5`,
  borde de 2px en los dos lados que forman la L) en las 4 esquinas de un
  panel — ver `CornerBracketPanel` más abajo. El color de los corchetes es
  independiente del borde del panel, para poder señalar un estado en vivo
  (ej. corchetes verdes = objetivo bloqueado) sin recolorear todo el panel.

## Animaciones (timing exacto — reproducir igual en Flutter)

| Nombre | Duración/curva | Efecto |
|---|---|---|
| `lock-pulse` | 1.4s ease-in-out infinite | Opacidad 1 → 0.45 → 1 (respiración). |
| `radar-sweep` | 4s linear infinite | Rotación 0° → 360°, `transform-origin: center`. |
| `scan-sweep` | 3.2s ease-in-out infinite | Traslación vertical -100% → 100%. |
| `pulse-ring` | 1.6s ease-out infinite | `scale(0.8)→scale(1.8)`, opacidad `0.6→0`. |

## Primitivos HUD (`app/frontend/src/components/hud/`)

### `CornerBracketPanel`
Reemplazo de "card": un `div` con borde hairline + fondo `panel`, sin
`border-radius`, más 4 `span` absolutos en las esquinas (los corchetes en
L). Props: `title?`, `color?: 'hairline'|'lock'|'warn'|'alert'`
(recolorea solo los corchetes), `pulse?: boolean` (aplica `lock-pulse` a
los corchetes), `padded?`, `compact?` (padding `p-2` en vez de `p-4`).

### `StatusBadge`
Punto de color (`h-1.5 w-1.5`) + texto en mayúsculas, mismo color de
texto que el punto. `status: 'lock'|'warn'|'alert'|'idle'`. El texto es
obligatorio — nunca solo el punto de color.

### `PageHeader`
Banner de cabecera de página: eyebrow `code` (p. ej. `SYS-01`) en
`accent` + `.field-label`, `title` en `h1` (`text-2xl`), `subtitle?`
opcional como chip con borde hairline (mono, 10px, tracking, texto
`ink-dim`), y un slot `action?` a la derecha (p. ej. botón de parada de
emergencia). No es sticky ni full-bleed — respeta el ancho del
contenedor que lo envuelve. Códigos actuales: Live View `SYS-01`, People
`SYS-02`, Manual Mode `SYS-03`, Room Scan `SYS-04`, Settings `SYS-05`.

### `MonoLabel`
Wrapper de la clase `.field-label` (11px, mayúsculas, tracking 0.14em,
`ink-dim`) para labels de campo/instrumento (`PAN`, `TILT`, `STATUS`).

### `TelemetryRow`
Tape gauge horizontal: label + barra con línea central + marcador
deslizante en `lock` posicionado por fracción `(valor-min)/(max-min)` +
valor numérico tabular a la derecha. Usado para lecturas de pan/tilt en
grados.

## Mapeo a Flutter (`app/mobile/lib/design_system/`)

| Web (Tailwind/CSS) | Flutter |
|---|---|
| `@theme` tokens de color | `ThemeExtension<AppColors>` en `tokens/app_colors.dart`, con un enum `StatusColor {lock,warn,alert,idle}` separado de `accent` para que no puedan mezclarse por error. |
| `font-cond` / `font-mono`, reglas de `h1-h3`/`button`/`.field-label` | `TextTheme` en `tokens/app_typography.dart` (Barlow Condensed + IBM Plex Mono vía `google_fonts` o assets embebidos), incluyendo `fieldLabelStyle` y `tabularStyle` (`FontFeature.tabularFigures()`). |
| Duraciones de keyframes | Constantes en `tokens/app_motion.dart`, una sola fuente para las 4 animaciones. |
| `CornerBracketPanel.tsx` | `widgets/corner_bracket_panel.dart` — `Stack` + 4 decoraciones de esquina posicionadas independientemente (igual que los 4 `span` del DOM real), no un único `CustomPainter` de panel completo. |
| `StatusBadge.tsx` | `widgets/status_badge.dart` — `Row` con punto + texto, mismo color, nunca solo el punto. |
| `PageHeader.tsx` | `widgets/page_header.dart` — mismo layout eyebrow/título/chip/acción. |
| `MonoLabel.tsx` | `widgets/mono_label.dart` sobre `app_typography.fieldLabelStyle`. |
| `TelemetryRow.tsx` | `widgets/telemetry_row.dart` — misma geometría por fracción, sin necesidad de `CustomPainter` (es posicionamiento simple). |
| `.animate-lock-pulse` / `-radar-sweep` / `-scan` / `-ping-ring` | `widgets/animations/{lock_pulse,radar_sweep,scan_sweep,pulse_ring}.dart`, cada uno un `AnimationController` reutilizable con la duración/curva de `app_motion.dart`. |
| Radares de detección (`LiveTrackingRadar`, `ScanRadarView`, en `components/video/`, no `hud/`) | Widgets locales de su feature (`features/live_view/.../live_tracking_radar.dart`, `features/room_scan/.../scan_radar_view.dart`), construidos con `CustomPainter` porque sí involucran geometría angular/arcos — no son primitivos de `design_system`, igual que en la web no viven en `components/hud/`. |
