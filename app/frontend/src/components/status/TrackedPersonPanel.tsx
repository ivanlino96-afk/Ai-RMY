import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import { UNKNOWN_LABEL } from '../../constants'
import type { Detection } from '../../types/api'

interface TrackedPersonPanelProps {
  detections: Detection[]
  className?: string
}

// RF-11: the pipeline reports every face in frame, not one primary target —
// this panel lists all of them rather than picking a single "target".
export function TrackedPersonPanel({ detections, className = '' }: TrackedPersonPanelProps) {
  const anyLocked = detections.some((detection) => detection.label !== null && detection.label !== UNKNOWN_LABEL)

  return (
    <CornerBracketPanel
      title="Target"
      color={anyLocked ? 'lock' : 'hairline'}
      pulse={anyLocked}
      className={`lg:flex lg:min-h-0 lg:flex-col ${className}`}
    >
      {detections.length === 0 ? (
        <p className="text-sm text-ink-dim">No target acquired.</p>
      ) : (
        <div className="space-y-3 lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
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
