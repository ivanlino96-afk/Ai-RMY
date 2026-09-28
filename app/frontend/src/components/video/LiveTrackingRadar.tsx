import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { UNKNOWN_LABEL } from '../../constants'
import type { Detection } from '../../types/api'

interface LiveTrackingRadarProps {
  detections: Detection[]
  frameWidth: number | null
  frameHeight: number | null
  armed: boolean
  className?: string
}

const VIEW = 260
const CENTER = VIEW / 2
const RADIUS = VIEW / 2 - 24
const RINGS = [0.25, 0.5, 0.75, 1]

// Circular scope, deliberately distinct from ScanRadarView's rectangular
// pan/tilt plot (that one is for discrete room-scan waypoints; this one is
// live, one point per detection in the current frame). Like ScanRadarView,
// this is an angular-deviation-from-frame-center readout, not a real
// range/distance sensor -- this camera has no depth/lidar, so the distance
// from center here is exactly the detection's pixel offset from the
// boresight, nothing more.
function offsetFraction(bbox: Detection['bbox'], frameWidth: number, frameHeight: number) {
  const [x, y, w, h] = bbox
  const cx = x + w / 2
  const cy = y + h / 2
  return {
    dx: (cx - frameWidth / 2) / (frameWidth / 2),
    dy: (cy - frameHeight / 2) / (frameHeight / 2),
  }
}

export function LiveTrackingRadar({ detections, frameWidth, frameHeight, armed, className = '' }: LiveTrackingRadarProps) {
  const sweepColor = armed ? 'stroke-alert' : 'stroke-ink-dim'
  const panelColor = armed ? 'alert' : 'hairline'

  const points =
    frameWidth && frameHeight
      ? detections.map((detection, index) => {
          const { dx, dy } = offsetFraction(detection.bbox, frameWidth, frameHeight)
          const magnitude = Math.min(Math.hypot(dx, dy), 1)
          const angle = Math.atan2(-dy, dx)
          const locked = detection.label !== null && detection.label !== UNKNOWN_LABEL
          return {
            key: index,
            x: CENTER + Math.cos(angle) * magnitude * RADIUS,
            y: CENTER - Math.sin(angle) * magnitude * RADIUS,
            locked,
          }
        })
      : []

  return (
    <CornerBracketPanel title="Live radar" color={panelColor} pulse={armed} className={`lg:flex lg:min-h-0 lg:flex-col ${className}`}>
      <div className="flex items-center justify-center lg:min-h-0 lg:flex-1">
        <svg viewBox={`0 0 ${VIEW} ${VIEW}`} className="w-full lg:h-full lg:w-auto">
          {RINGS.map((fraction) => (
            <circle
              key={fraction}
              cx={CENTER}
              cy={CENTER}
              r={RADIUS * fraction}
              className="fill-none stroke-hairline"
              strokeDasharray="2,3"
            />
          ))}
          <line x1={CENTER - RADIUS} y1={CENTER} x2={CENTER + RADIUS} y2={CENTER} className="stroke-hairline" strokeDasharray="2,3" />
          <line x1={CENTER} y1={CENTER - RADIUS} x2={CENTER} y2={CENTER + RADIUS} className="stroke-hairline" strokeDasharray="2,3" />

          <line
            x1={CENTER}
            y1={CENTER}
            x2={CENTER}
            y2={CENTER - RADIUS}
            className={`animate-radar-sweep ${sweepColor}`}
          />

          {points.map((point) => (
            <circle
              key={point.key}
              cx={point.x}
              cy={point.y}
              r={4}
              className={point.locked ? 'fill-lock' : 'fill-alert'}
            />
          ))}
        </svg>
      </div>

      {points.length === 0 ? <p className="mt-2 text-sm text-ink-dim">No contacts.</p> : null}
    </CornerBracketPanel>
  )
}
