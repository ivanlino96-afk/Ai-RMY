import { useArmDefense, useDisarmDefense } from '../../api/defense'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'
import type { DefenseStatus } from '../../types/api'

interface DefenseModePanelProps {
  status: DefenseStatus | null
}

const THREAT_WINDOW_S = 60

// Derived purely from the log already on `status` -- no new endpoint. Just a
// glanceable summary of how "hot" the last minute has been, on top of the
// full history in DefenseLogPanel.
function threatLevel(status: DefenseStatus | null): { status: 'idle' | 'warn' | 'alert'; label: string } {
  const log = status?.log ?? []
  const cutoff = Date.now() / 1000 - THREAT_WINDOW_S
  const recentThreats = log.filter((entry) => entry.type === 'threat' && entry.timestamp >= cutoff).length

  if (recentThreats >= 2) return { status: 'alert', label: 'threat level: high' }
  if (recentThreats === 1) return { status: 'warn', label: 'threat level: elevated' }
  return { status: 'idle', label: 'threat level: low' }
}

// Arming forces tracking on and prioritizes the unrecognized face (see
// Pipeline._select_target) -- this panel only owns the arm/disarm toggle,
// not the tracking state itself.
export function DefenseModePanel({ status }: DefenseModePanelProps) {
  const arm = useArmDefense()
  const disarm = useDisarmDefense()
  const active = status?.active ?? false
  const pending = arm.isPending || disarm.isPending
  const level = threatLevel(status)

  return (
    <CornerBracketPanel title="Defense mode" color={active ? 'alert' : 'hairline'} pulse={active} compact>
      <div className="space-y-1.5">
        <StatusBadge status={active ? 'alert' : 'idle'} label={active ? 'armed' : 'disarmed'} />
        {active ? <StatusBadge status={level.status} label={level.label} /> : null}

        <button
          type="button"
          onClick={() => (active ? disarm.mutate() : arm.mutate())}
          disabled={pending}
          className="w-full border border-alert px-3 py-1 text-xs tracking-[0.1em] text-alert uppercase hover:bg-alert hover:text-void disabled:opacity-40"
        >
          {active ? 'Desactivar alarma' : 'Activar alarma'}
        </button>
      </div>
    </CornerBracketPanel>
  )
}
