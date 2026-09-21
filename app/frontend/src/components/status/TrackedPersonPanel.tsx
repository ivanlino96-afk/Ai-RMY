import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import { UNKNOWN_LABEL } from '../../constants'
import type { Detection } from '../../types/api'

interface TrackedPersonPanelProps {
  detections: Detection[]
}

// RF-11: the pipeline reports every face in frame, not one primary target —
// this panel lists all of them rather than picking a single "target".
export function TrackedPersonPanel({ detections }: TrackedPersonPanelProps) {
  const anyLocked = detections.some((detection) => detection.label !== null && detection.label !== UNKNOWN_LABEL)

  return (
    <CornerBracketPanel title="Target" color={anyLocked ? 'lock' : 'hairline'} pulse={anyLocked}>
      {detections.length === 0 ? (
        <p className="text-sm text-ink-dim">No target acquired.</p>
      ) : (
        <div className="space-y-3">
          {detections.map((detection, index) => {
            const locked = detection.label !== null && detection.label !== UNKNOWN_LABEL
            return (
              <div key={index} className="space-y-1">
                <div className="flex items-baseline justify-between">
                  <MonoLabel>Name</MonoLabel>
                  <span className={locked ? 'text-lock' : 'text-alert'}>
                    {(detection.label ?? UNKNOWN_LABEL).toUpperCase()}
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <MonoLabel>Conf</MonoLabel>
                  <span className="tabular text-ink">{Math.round(detection.score * 100)}%</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </CornerBracketPanel>
  )
}
