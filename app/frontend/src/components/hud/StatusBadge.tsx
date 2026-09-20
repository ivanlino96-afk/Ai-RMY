export type Status = 'lock' | 'warn' | 'alert' | 'idle'

const STATUS_DOT: Record<Status, string> = {
  lock: 'bg-lock',
  warn: 'bg-warn',
  alert: 'bg-alert',
  idle: 'bg-ink-dim',
}

const STATUS_TEXT: Record<Status, string> = {
  lock: 'text-lock',
  warn: 'text-warn',
  alert: 'text-alert',
  idle: 'text-ink-dim',
}

interface StatusBadgeProps {
  status: Status
  label: string
}

// Status is always color + text together, never color alone.
export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center gap-2 text-xs tracking-[0.1em] ${STATUS_TEXT[status]}`}>
      <span className={`h-1.5 w-1.5 shrink-0 ${STATUS_DOT[status]}`} />
      {label.toUpperCase()}
    </span>
  )
}
