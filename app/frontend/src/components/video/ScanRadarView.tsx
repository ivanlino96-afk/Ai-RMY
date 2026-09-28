import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import type { ScanWaypoint } from '../../types/api'

interface ScanRadarViewProps {
  results: ScanWaypoint[]
  panRangeDeg: [number, number]
  tiltRangeDeg: [number, number]
}

const VIEW_W = 400
const VIEW_H = 300
const MARGIN = 28

// No charting library is installed anywhere in this app (package.json has
// only react-router-dom/react-query/tailwind) -- this is a hand-rolled
// inline SVG plot, not a wrapper around one.
//
// This is a 2D angular inventory, not a distance/3D map (see AGENTS.md's
// rule against claiming absolute position without homing): each point is
// "object seen at this pan/tilt", nothing more.
export function ScanRadarView({ results, panRangeDeg, tiltRangeDeg }: ScanRadarViewProps) {
  const [panLo, panHi] = panRangeDeg
  const [tiltLo, tiltHi] = tiltRangeDeg

  const toX = (panDeg: number) => {
    const span = panHi - panLo || 1
    return MARGIN + ((panDeg - panLo) / span) * (VIEW_W - 2 * MARGIN)
  }
  // Inverted: positive tilt (looking up) plots higher on screen.
  const toY = (tiltDeg: number) => {
    const span = tiltHi - tiltLo || 1
    return VIEW_H - MARGIN - ((tiltDeg - tiltLo) / span) * (VIEW_H - 2 * MARGIN)
  }

  const points = results.flatMap((waypoint) =>
    waypoint.objects.length > 0
      ? waypoint.objects.map((object, i) => ({
          key: `${waypoint.pan_deg},${waypoint.tilt_deg},${i}`,
          x: toX(waypoint.pan_deg),
          y: toY(waypoint.tilt_deg),
          label: object.label,
          empty: false,
        }))
      : [
          {
            key: `${waypoint.pan_deg},${waypoint.tilt_deg}`,
            x: toX(waypoint.pan_deg),
            y: toY(waypoint.tilt_deg),
            label: '',
            empty: true,
          },
        ]
  )

  return (
    <CornerBracketPanel title="Angular object inventory">
      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="w-full text-ink-dim">
        <rect
          x={MARGIN}
          y={MARGIN}
          width={VIEW_W - 2 * MARGIN}
          height={VIEW_H - 2 * MARGIN}
          className="fill-none stroke-hairline"
        />
        <line
          x1={toX(0)}
          y1={MARGIN}
          x2={toX(0)}
          y2={VIEW_H - MARGIN}
          className="stroke-hairline"
          strokeDasharray="2,3"
        />
        <line
          x1={MARGIN}
          y1={toY(0)}
          x2={VIEW_W - MARGIN}
          y2={toY(0)}
          className="stroke-hairline"
          strokeDasharray="2,3"
        />

        <text x={MARGIN} y={VIEW_H - MARGIN + 14} className="fill-current text-[9px]">
          {panLo}°
        </text>
        <text x={VIEW_W - MARGIN} y={VIEW_H - MARGIN + 14} textAnchor="end" className="fill-current text-[9px]">
          {panHi}°
        </text>
        <text x={MARGIN - 6} y={MARGIN + 4} textAnchor="end" className="fill-current text-[9px]">
          {tiltHi}°
        </text>
        <text x={MARGIN - 6} y={VIEW_H - MARGIN} textAnchor="end" className="fill-current text-[9px]">
          {tiltLo}°
        </text>

        {points.map((point) =>
          point.empty ? (
            <circle key={point.key} cx={point.x} cy={point.y} r={2} className="fill-ink-dim opacity-50" />
          ) : (
            <g key={point.key}>
              <circle cx={point.x} cy={point.y} r={3.5} className="fill-lock" />
              <text
                x={point.x + 6}
                y={point.y + 3}
                className="fill-ink text-[9px] tracking-[0.04em] uppercase"
              >
                {point.label}
              </text>
            </g>
          )
        )}
      </svg>

      {results.length === 0 ? (
        <MonoLabel className="mt-2 block text-ink-dim">No scan results yet</MonoLabel>
      ) : null}
    </CornerBracketPanel>
  )
}
