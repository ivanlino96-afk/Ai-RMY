import { MonoLabel } from './MonoLabel'

interface TelemetryRowProps {
  label: string
  valueDeg: number
  min?: number
  max?: number
}

// A graduated tape gauge, like a pan/tilt readout on a real camera mount —
// the tick marks and marker encode range/position, the number is the
// precise value. Ticks are load-bearing, not decoration.
export function TelemetryRow({ label, valueDeg, min = -90, max = 90 }: TelemetryRowProps) {
  const clamped = Math.min(max, Math.max(min, valueDeg))
  const fraction = (clamped - min) / (max - min)

  return (
    <div className="flex items-center gap-3">
      <MonoLabel className="w-10 shrink-0">{label}</MonoLabel>
      <div className="relative h-3 flex-1 border-y border-hairline">
        <div className="absolute inset-y-0 left-1/2 w-px bg-hairline" />
        <div
          className="absolute top-1/2 h-2.5 w-0.5 -translate-y-1/2 bg-lock"
          style={{ left: `calc(${fraction * 100}% - 1px)` }}
        />
      </div>
      <span className="tabular w-14 shrink-0 text-right text-sm text-ink">
        {valueDeg.toFixed(1)}°
      </span>
    </div>
  )
}
