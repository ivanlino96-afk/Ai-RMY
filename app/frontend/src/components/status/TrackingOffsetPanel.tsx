import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'
import { TelemetryRow } from '../hud/TelemetryRow'
import type { TrackingOffset } from '../../types/api'

interface TrackingOffsetPanelProps {
  offset: TrackingOffset | null
  frameWidth: number | null
  frameHeight: number | null
}

// Same numbers vision/pipeline.py computes and sends to the ESP32 via
// TrackingController.compute() — this panel only displays them, it does
// not recompute the geometry independently.
export function TrackingOffsetPanel({ offset, frameWidth, frameHeight }: TrackingOffsetPanelProps) {
  const maxDx = (frameWidth ?? 0) / 2
  const maxDy = (frameHeight ?? 0) / 2

  return (
    <CornerBracketPanel title="Centering" color={offset === null ? 'hairline' : offset.centered ? 'lock' : 'warn'}>
      {offset === null ? (
        <p className="text-sm text-ink-dim">No target acquired.</p>
      ) : (
        <div className="space-y-3">
          <TelemetryRow label="dX" valueDeg={offset.dx} min={-maxDx} max={maxDx} unit="px" />
          <TelemetryRow label="dY" valueDeg={offset.dy} min={-maxDy} max={maxDy} unit="px" />
          <TelemetryRow label="Pan" valueDeg={offset.pan_deg} />
          <TelemetryRow label="Tilt" valueDeg={offset.tilt_deg} />

          <div className="pt-1">
            <StatusBadge status={offset.centered ? 'lock' : 'warn'} label={offset.centered ? 'centered' : 'correcting'} />
          </div>
        </div>
      )}
    </CornerBracketPanel>
  )
}
