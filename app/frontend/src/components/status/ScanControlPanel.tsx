import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { MonoLabel } from '../hud/MonoLabel'
import { StatusBadge } from '../hud/StatusBadge'
import type { ScanStatus } from '../../types/api'

interface ScanControlPanelProps {
  trackingEnabled: boolean
  scanState: ScanStatus['state']
  progress: number
  resultCount: number
  startPending: boolean
  cancelPending: boolean
  onStart: () => void
  onCancel: () => void
}

// Dumb panel: the page owns the start/cancel mutations and passes down
// exactly the state needed to render (same split as JogAxisPanel).
export function ScanControlPanel({
  trackingEnabled,
  scanState,
  progress,
  resultCount,
  startPending,
  cancelPending,
  onStart,
  onCancel,
}: ScanControlPanelProps) {
  const running = scanState === 'running'
  const canStart = !trackingEnabled && !running && !startPending

  return (
    <CornerBracketPanel title="Room scan" color={running ? 'lock' : 'hairline'}>
      <div className="space-y-3">
        <StatusBadge
          status={running ? 'lock' : scanState === 'done' ? 'idle' : 'idle'}
          label={running ? 'scanning' : scanState === 'done' ? 'last scan done' : 'idle'}
        />

        {running ? (
          <div className="space-y-1">
            <MonoLabel>Progress</MonoLabel>
            <div className="h-1.5 w-full bg-void">
              <div
                className="h-1.5 bg-lock transition-[width]"
                style={{ width: `${Math.round(progress * 100)}%` }}
              />
            </div>
            <p className="text-xs text-ink-dim tabular">
              {Math.round(progress * 100)}% — {resultCount} waypoint{resultCount === 1 ? '' : 's'} scanned
            </p>
          </div>
        ) : null}

        {trackingEnabled ? (
          <MonoLabel className="text-warn">Disable tracking to start a scan</MonoLabel>
        ) : null}

        {running ? (
          <button
            type="button"
            onClick={onCancel}
            disabled={cancelPending}
            className="w-full border border-alert px-3 py-2 text-xs tracking-[0.1em] text-alert uppercase hover:bg-alert hover:text-void disabled:opacity-40"
          >
            Cancel scan
          </button>
        ) : (
          <button
            type="button"
            onClick={onStart}
            disabled={!canStart}
            className="w-full border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock disabled:opacity-40"
          >
            Start scan
          </button>
        )}
      </div>
    </CornerBracketPanel>
  )
}
