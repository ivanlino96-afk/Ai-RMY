import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import { UNKNOWN_LABEL } from '../../constants'
import type { Detection } from '../../types/api'

interface TrackedPersonPanelProps {
  detection: Detection | null
}

export function TrackedPersonPanel({ detection }: TrackedPersonPanelProps) {
  const locked = detection !== null && detection.label !== null && detection.label !== UNKNOWN_LABEL

  return (
    <CornerBracketPanel title="Target" color={locked ? 'lock' : 'hairline'} pulse={locked}>
      {detection ? (
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <MonoLabel>Name</MonoLabel>
            <span className={locked ? 'text-lock' : 'text-warn'}>
              {(detection.label ?? UNKNOWN_LABEL).toUpperCase()}
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <MonoLabel>Conf</MonoLabel>
            <span className="tabular text-ink">{Math.round(detection.score * 100)}%</span>
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink-dim">No target acquired.</p>
      )}
    </CornerBracketPanel>
  )
}
