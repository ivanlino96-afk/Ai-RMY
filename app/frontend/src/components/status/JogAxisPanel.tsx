import { useState } from 'react'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import { TelemetryRow } from '../hud/TelemetryRow'

interface JogAxisPanelProps {
  label: string
  currentDeg: number
  min: number
  max: number
  disabled: boolean
  pending: boolean
  onJog: (deltaDeg: number) => void
}

// One motor, jogged independently of the other — see docs/protocol.md's
// move_delta: passing 0 on the other axis leaves it untouched.
export function JogAxisPanel({ label, currentDeg, min, max, disabled, pending, onJog }: JogAxisPanelProps) {
  const [amount, setAmount] = useState('10')
  const parsed = Number.parseFloat(amount)
  const canJog = !disabled && !pending && Number.isFinite(parsed) && parsed !== 0

  return (
    <CornerBracketPanel title={`${label} axis`}>
      <div className="space-y-3">
        <TelemetryRow label={label} valueDeg={currentDeg} min={min} max={max} />

        <div className="flex items-center gap-2 pt-1">
          <input
            type="number"
            step="0.1"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={disabled}
            aria-label={`${label} jog amount, degrees`}
            className="w-20 border border-hairline bg-void px-2 py-2 text-sm text-ink tabular disabled:opacity-40"
          />
          <span className="text-xs text-ink-dim">°</span>

          <button
            type="button"
            onClick={() => canJog && onJog(-Math.abs(parsed))}
            disabled={!canJog}
            className="border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock disabled:opacity-40"
          >
            − Move
          </button>
          <button
            type="button"
            onClick={() => canJog && onJog(Math.abs(parsed))}
            disabled={!canJog}
            className="flex-1 border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock disabled:opacity-40"
          >
            + Move
          </button>
        </div>

        {disabled ? (
          <MonoLabel className="text-warn">Disable tracking to jog</MonoLabel>
        ) : null}
      </div>
    </CornerBracketPanel>
  )
}
