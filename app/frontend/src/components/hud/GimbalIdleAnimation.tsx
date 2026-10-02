const VIEW_W = 400
const VIEW_H = 266

const TURRET_CX = 210
const PIVOT_Y = 118

const FLOOR_TOP = { l: 160, r: 260, y: 190 }
const FLOOR_BOTTOM = { l: 30, r: 370, y: 248 }
const FLOOR_STEPS = [0, 0.25, 0.5, 0.75, 1]
const FLOOR_COLUMNS = [0.25, 0.5, 0.75]

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

function floorRung(t: number) {
  return {
    y: lerp(FLOOR_TOP.y, FLOOR_BOTTOM.y, t),
    l: lerp(FLOOR_TOP.l, FLOOR_BOTTOM.l, t),
    r: lerp(FLOOR_TOP.r, FLOOR_BOTTOM.r, t),
  }
}

const DISCS = [
  { cy: 205, rx: 58, ry: 17 },
  { cy: 193, rx: 52, ry: 15 },
  { cy: 182, rx: 46, ry: 13 },
]

const LEG_FEET = [
  { x: 100, y: 246 },
  { x: 210, y: 254 },
  { x: 320, y: 246 },
]

const CALLOUTS = [
  { label: 'Camera', sub: 'Detect · track', y: 78, top: '24%' },
  { label: 'Elevation axis', sub: 'Tilt drive', y: 112, top: '39%' },
  { label: 'Pan drive', sub: 'Azimuth', y: 160, top: '56%' },
  { label: 'Slewing ring', sub: 'Base mount', y: 196, top: '71%' },
]

const CALLOUT_TARGET_X = 196
const CALLOUT_LABEL_X = 150

// Isometric spec-sheet illustration of the pan-tilt turret, redrawn as a
// pure wireframe (stroke only, no filled faces) over a perspective floor
// grid — a fixed base/mast plus a rotating head group (`animate-gimbal-pan`)
// that stands in for the azimuth stage. Deliberately drops the laser/
// designator motif from the outside reference this was inspired by: Ai-RMY
// is a camera-only tracking rig, not a targeting system, so the only accent
// highlight is the lens ring. Hand-rolled inline SVG, same approach as
// LiveTrackingRadar/ScanRadarView — no canvas, no 3D/charting library.
export function GimbalIdleAnimation() {
  return (
    <div className="flex h-full min-h-[280px] items-center justify-center">
      <div className="relative aspect-[400/266] w-full max-w-[460px]">
        <span className="absolute top-0 left-0 h-3.5 w-3.5 border-t-2 border-l-2 border-hairline" />
        <span className="absolute top-0 right-0 h-3.5 w-3.5 border-t-2 border-r-2 border-hairline" />
        <span className="absolute bottom-0 left-0 h-3.5 w-3.5 border-b-2 border-l-2 border-hairline" />
        <span className="absolute right-0 bottom-0 h-3.5 w-3.5 border-r-2 border-b-2 border-hairline" />

        <div className="absolute top-2 left-3">
          <p className="field-label text-ink">Fig.01 · Isometric</p>
          <p className="field-label">Ai-RMY · Pan-tilt tracker</p>
        </div>
        <p className="field-label absolute top-2 right-3 text-right">Sys-00 · Sht 1/1</p>

        <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="h-full w-full">
          {FLOOR_STEPS.map((t) => {
            const rung = floorRung(t)
            return (
              <line key={t} x1={rung.l} y1={rung.y} x2={rung.r} y2={rung.y} className="stroke-hairline" strokeWidth={1} />
            )
          })}
          <line x1={FLOOR_TOP.l} y1={FLOOR_TOP.y} x2={FLOOR_BOTTOM.l} y2={FLOOR_BOTTOM.y} className="stroke-hairline" strokeWidth={1} />
          <line x1={FLOOR_TOP.r} y1={FLOOR_TOP.y} x2={FLOOR_BOTTOM.r} y2={FLOOR_BOTTOM.y} className="stroke-hairline" strokeWidth={1} />
          {FLOOR_COLUMNS.map((f) => (
            <line
              key={f}
              x1={lerp(FLOOR_TOP.l, FLOOR_TOP.r, f)}
              y1={FLOOR_TOP.y}
              x2={lerp(FLOOR_BOTTOM.l, FLOOR_BOTTOM.r, f)}
              y2={FLOOR_BOTTOM.y}
              className="stroke-hairline"
              strokeWidth={1}
            />
          ))}

          {LEG_FEET.map((foot) => (
            <g key={`${foot.x}-${foot.y}`}>
              <line x1={TURRET_CX} y1={210} x2={foot.x} y2={foot.y} className="stroke-ink-dim" strokeWidth={1.5} />
              <line
                x1={foot.x - 10}
                y1={foot.y}
                x2={foot.x + 10}
                y2={foot.y}
                className="stroke-ink-dim"
                strokeWidth={1.5}
              />
            </g>
          ))}

          {DISCS.map((disc) => (
            <ellipse
              key={disc.cy}
              cx={TURRET_CX}
              cy={disc.cy}
              rx={disc.rx}
              ry={disc.ry}
              className="fill-none stroke-ink-dim"
              strokeWidth={1.5}
            />
          ))}

          <circle cx={TURRET_CX - 14} cy={166} r={14} className="fill-none stroke-ink-dim" strokeWidth={1.5} />
          <circle cx={TURRET_CX + 14} cy={166} r={14} className="fill-none stroke-ink-dim" strokeWidth={1.5} />
          <circle cx={TURRET_CX} cy={158} r={9} className="fill-void stroke-ink-dim" strokeWidth={1.5} />
          <line x1={TURRET_CX - 14} y1={152} x2={TURRET_CX + 14} y2={152} className="stroke-ink-dim" strokeWidth={1} />
          <line x1={TURRET_CX - 14} y1={180} x2={TURRET_CX + 14} y2={180} className="stroke-ink-dim" strokeWidth={1} />

          <line x1={TURRET_CX} y1={149} x2={TURRET_CX} y2={PIVOT_Y} className="stroke-ink-dim" strokeWidth={2} />
          <circle cx={TURRET_CX} cy={PIVOT_Y} r={6} className="fill-void stroke-ink-dim" strokeWidth={1.5} />

          {CALLOUTS.map((callout) => (
            <g key={callout.label}>
              <line x1={CALLOUT_LABEL_X} y1={callout.y} x2={CALLOUT_TARGET_X} y2={callout.y} className="stroke-ink-dim" strokeWidth={1} />
              <circle cx={CALLOUT_TARGET_X} cy={callout.y} r={2.5} className="fill-ink-dim" />
            </g>
          ))}

          <g className="animate-gimbal-pan" style={{ transformOrigin: `${TURRET_CX}px ${PIVOT_Y}px` }}>
            <line x1={TURRET_CX - 14} y1={PIVOT_Y} x2={TURRET_CX - 14} y2={95} className="stroke-ink-dim" strokeWidth={2} />
            <line x1={TURRET_CX + 14} y1={PIVOT_Y} x2={TURRET_CX + 14} y2={95} className="stroke-ink-dim" strokeWidth={2} />
            <line x1={TURRET_CX - 14} y1={95} x2={TURRET_CX + 14} y2={95} className="stroke-ink-dim" strokeWidth={1.5} />
            <circle cx={TURRET_CX - 14} cy={95} r={2} className="fill-ink-dim" />
            <circle cx={TURRET_CX + 14} cy={95} r={2} className="fill-ink-dim" />

            <rect x={TURRET_CX - 28} y={55} width={56} height={40} className="fill-void stroke-ink-dim" strokeWidth={1.5} />
            <polygon
              points={`${TURRET_CX - 28},55 ${TURRET_CX + 28},55 ${TURRET_CX + 42},41 ${TURRET_CX - 14},41`}
              className="fill-void stroke-ink-dim"
              strokeWidth={1.5}
            />
            <polygon
              points={`${TURRET_CX + 28},55 ${TURRET_CX + 28},95 ${TURRET_CX + 42},81 ${TURRET_CX + 42},41`}
              className="fill-void stroke-ink-dim"
              strokeWidth={1.5}
            />

            <circle cx={TURRET_CX - 28} cy={55} r={2} className="fill-ink-dim" />
            <circle cx={TURRET_CX + 28} cy={55} r={2} className="fill-ink-dim" />
            <circle cx={TURRET_CX - 28} cy={95} r={2} className="fill-ink-dim" />
            <circle cx={TURRET_CX + 28} cy={95} r={2} className="fill-ink-dim" />
            <circle cx={TURRET_CX + 14} cy={48} r={3} className="fill-accent animate-lock-pulse" />

            <circle cx={TURRET_CX} cy={75} r={13} className="fill-void stroke-ink-dim" strokeWidth={1.5} />
            <circle cx={TURRET_CX} cy={75} r={7} className="fill-none stroke-accent" strokeWidth={2} />
            <circle cx={TURRET_CX} cy={75} r={7} className="fill-none stroke-accent animate-ping-ring" strokeWidth={2} />
          </g>
        </svg>

        {CALLOUTS.map((callout) => (
          <div
            key={callout.label}
            className="absolute text-right"
            style={{ right: `${100 - (CALLOUT_LABEL_X / VIEW_W) * 100}%`, top: callout.top }}
          >
            <p className="field-label border-b border-hairline pb-0.5 text-ink">{callout.label}</p>
            <p className="field-label mt-0.5">{callout.sub}</p>
          </div>
        ))}

        <div className="absolute bottom-2 left-3 flex gap-3">
          <p className="field-label">Idle · standby</p>
          <p className="field-label">Auto-track · face ID</p>
        </div>

        <div className="absolute right-3 bottom-2 w-[34%] border border-hairline bg-panel p-1.5">
          <span className="absolute top-0 left-0 h-2 w-2 border-t border-l border-accent" />
          <span className="absolute top-0 right-0 h-2 w-2 border-t border-r border-accent" />
          <span className="absolute bottom-0 left-0 h-2 w-2 border-b border-l border-accent" />
          <span className="absolute right-0 bottom-0 h-2 w-2 border-r border-b border-accent" />
          <p className="field-label text-center text-[9px]">Camera view</p>
          <div className="relative mt-1 h-12 border border-hairline">
            <span className="absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 border border-accent" />
            <span className="absolute top-1/2 left-1/2 h-1 w-1 -translate-x-1/2 -translate-y-1/2 bg-accent" />
            <p className="field-label absolute top-0.5 left-0.5 text-[8px] text-accent">Track · lock</p>
            <p className="field-label absolute right-0.5 bottom-0.5 text-[8px] text-accent">Designated</p>
          </div>
        </div>
      </div>
    </div>
  )
}
