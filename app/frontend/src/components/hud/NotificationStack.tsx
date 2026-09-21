import type { NotificationItem, NotificationKind } from '../../hooks/useNotifications'

interface NotificationStackProps {
  notifications: NotificationItem[]
  onDismiss: (id: number) => void
}

const KIND_CLASS: Record<NotificationKind, string> = {
  info: 'border-lock text-lock',
  warn: 'border-warn text-warn',
  alert: 'border-alert text-alert',
}

export function NotificationStack({ notifications, onDismiss }: NotificationStackProps) {
  if (notifications.length === 0) return null

  return (
    <div className="pointer-events-none fixed bottom-6 right-6 z-20 flex w-full max-w-xs flex-col gap-2">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`pointer-events-auto flex items-start gap-3 border bg-panel px-3 py-2 text-xs ${KIND_CLASS[notification.kind]}`}
        >
          <span className="flex-1">{notification.message}</span>
          <button
            type="button"
            onClick={() => onDismiss(notification.id)}
            className="text-ink-dim hover:text-ink"
            aria-label="Dismiss"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}
