import { useGimbalStatus, useJogGimbal, useSetTrackingMode, useStopGimbal } from '../api/gimbal'
import { CornerBracketPanel } from '../components/hud/CornerBracketPanel'
import { StatusBadge } from '../components/hud/StatusBadge'
import { JogAxisPanel } from '../components/status/JogAxisPanel'
import type { useDetectionSocket } from '../hooks/useDetectionSocket'

interface ManualModePageProps {
  detection: ReturnType<typeof useDetectionSocket>
}

// Bench-testing screen: jog pan/tilt independently by an entered amount, in
// degrees, reusing the same move_delta command (and its firmware soft-limit
// clamping) the auto-tracker uses -- see docs/protocol.md.
export function ManualModePage({ detection }: ManualModePageProps) {
  const { data: status } = useGimbalStatus()
  const setTrackingMode = useSetTrackingMode()
  const jog = useJogGimbal()
  const stop = useStopGimbal()

  const telemetry = status?.telemetry ?? null
  const trackingEnabled = status?.tracking_enabled ?? true
  const jogDisabled = trackingEnabled

  return (
    <div className="space-y-6">
      {trackingEnabled ? (
        <CornerBracketPanel color="warn">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-warn">
              Tracking is active — disable it before jogging motors manually, so the
              auto-tracker doesn't fight your input.
            </p>
            <button
              type="button"
              onClick={() => setTrackingMode.mutate(false)}
              disabled={setTrackingMode.isPending}
              className="border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-warn hover:text-warn disabled:opacity-40"
            >
              Disable tracking
            </button>
          </div>
        </CornerBracketPanel>
      ) : null}

      <div className="flex items-center gap-4">
        <StatusBadge status={telemetry?.moving ? 'warn' : 'idle'} label={telemetry?.moving ? 'moving' : 'holding'} />
        <StatusBadge status={detection.event?.serial_connected ? 'lock' : 'alert'} label={detection.event?.serial_connected ? 'gimbal online' : 'gimbal offline'} />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <JogAxisPanel
          label="Pan"
          currentDeg={telemetry?.pan_deg ?? 0}
          min={-180}
          max={180}
          disabled={jogDisabled}
          pending={jog.isPending}
          onJog={(deltaDeg) => jog.mutate({ pan_deg: deltaDeg })}
        />
        <JogAxisPanel
          label="Tilt"
          currentDeg={telemetry?.tilt_deg ?? 0}
          min={-90}
          max={90}
          disabled={jogDisabled}
          pending={jog.isPending}
          onJog={(deltaDeg) => jog.mutate({ tilt_deg: deltaDeg })}
        />
      </div>

      <button
        type="button"
        onClick={() => stop.mutate()}
        disabled={stop.isPending}
        className="w-full border border-alert px-3 py-3 text-sm tracking-[0.2em] text-alert uppercase hover:bg-alert hover:text-void disabled:opacity-40"
      >
        Emergency stop
      </button>
    </div>
  )
}
