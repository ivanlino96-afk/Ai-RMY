import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'
import type { DefenseLogEntry } from '../../types/api'

interface DefenseLogPanelProps {
  log: DefenseLogEntry[]
  className?: string
}

function formatTime(timestamp: number) {
  return new Date(timestamp * 1000).toLocaleTimeString()
}

function downloadLog(log: DefenseLogEntry[]) {
  const header = 'timestamp,type,name,photo'
  const rows = log.map((entry) =>
    [new Date(entry.timestamp * 1000).toISOString(), entry.type, entry.name ?? '', entry.photo ?? ''].join(','),
  )
  const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `defense-log-${Date.now()}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

// Dumb panel: no fetching of its own -- the page passes down whichever log
// array is current (WS event first, status poll as fallback), same split as
// TrackedPersonPanel/DetectionOverlay.
export function DefenseLogPanel({ log, className = '' }: DefenseLogPanelProps) {
  const entries = [...log].reverse()

  return (
    <CornerBracketPanel title="Defense log" className={`lg:flex lg:min-h-0 lg:flex-col ${className}`}>
      {log.length > 0 ? (
        <button
          type="button"
          onClick={() => downloadLog(log)}
          className="mb-3 w-full shrink-0 border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock"
        >
          Download report
        </button>
      ) : null}

      {entries.length === 0 ? (
        <p className="text-sm text-ink-dim">No defense events yet.</p>
      ) : (
        <div className="max-h-64 space-y-2 overflow-y-auto lg:max-h-none lg:min-h-0 lg:flex-1">
          {entries.map((entry, index) => (
            <div key={index} className="flex items-center justify-between gap-3 border-b border-hairline pb-2">
              {entry.type === 'threat' ? (
                <>
                  <StatusBadge status="alert" label="threat" />
                  {entry.photo ? (
                    <img
                      src={`/api/defense/photo/${entry.photo}`}
                      alt="Suspect"
                      className="h-10 w-10 border border-alert object-cover"
                    />
                  ) : null}
                </>
              ) : (
                <StatusBadge status="lock" label={entry.name ?? 'identified'} />
              )}
              <span className="shrink-0 text-xs text-ink-dim tabular">{formatTime(entry.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </CornerBracketPanel>
  )
}
