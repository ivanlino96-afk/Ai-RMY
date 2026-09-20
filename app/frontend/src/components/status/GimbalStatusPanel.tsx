import { useCenterGimbal, useSetTrackingMode } from '../../api/gimbal'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'
import { TelemetryRow } from '../hud/TelemetryRow'
import type { GimbalStatus } from '../../types/api'

interface GimbalStatusPanelProps {
  status: GimbalStatus | undefined
}

export function GimbalStatusPanel({ status }: GimbalStatusPanelProps) {
  const center = useCenterGimbal()
  const setTrackingMode = useSetTrackingMode()
  const telemetry = status?.telemetry ?? null
  const trackingEnabled = status?.tracking_enabled ?? false

  return (
    <CornerBracketPanel title="Gimbal">
      <div className="space-y-3">
        <TelemetryRow label="Pan" valueDeg={telemetry?.pan_deg ?? 0} min={-180} max={180} />
        <TelemetryRow label="Tilt" valueDeg={telemetry?.tilt_deg ?? 0} min={-90} max={90} />

        <div className="flex items-center gap-4 pt-1">
          <StatusBadge status={telemetry?.moving ? 'warn' : 'idle'} label={telemetry?.moving ? 'moving' : 'holding'} />
          <StatusBadge status={telemetry?.homed ? 'lock' : 'idle'} label={telemetry?.homed ? 'homed' : 'unhomed'} />
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="button"
            onClick={() => center.mutate()}
            disabled={center.isPending}
            className="flex-1 border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock disabled:opacity-40"
          >
            Center
          </button>
          <button
            type="button"
            onClick={() => setTrackingMode.mutate(!trackingEnabled)}
            disabled={setTrackingMode.isPending}
            className="flex-1 border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-warn hover:text-warn disabled:opacity-40"
          >
            {trackingEnabled ? 'Pause tracking' : 'Resume tracking'}
          </button>
        </div>
      </div>
    </CornerBracketPanel>
  )
}
