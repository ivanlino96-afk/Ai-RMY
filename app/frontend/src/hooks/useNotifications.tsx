import { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { NotificationStack } from '../components/hud/NotificationStack'

export type NotificationKind = 'info' | 'warn' | 'alert'

export interface NotificationItem {
  id: number
  kind: NotificationKind
  message: string
}

interface NotificationsContextValue {
  notify: (message: string, kind?: NotificationKind) => void
}

const NotificationsContext = createContext<NotificationsContextValue | null>(null)

const AUTO_DISMISS_MS = 6000

// RF-16 requires one notification per connect/disconnect event with no cap
// on repeats, so this is a plain append-only stack (each auto-dismisses on
// its own timer) rather than a single "latest status" banner.
export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const nextId = useRef(0)

  const dismiss = useCallback((id: number) => {
    setNotifications((current) => current.filter((notification) => notification.id !== id))
  }, [])

  const notify = useCallback(
    (message: string, kind: NotificationKind = 'info') => {
      const id = nextId.current++
      setNotifications((current) => [...current, { id, kind, message }])
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS)
    },
    [dismiss],
  )

  return (
    <NotificationsContext.Provider value={{ notify }}>
      {children}
      <NotificationStack notifications={notifications} onDismiss={dismiss} />
    </NotificationsContext.Provider>
  )
}

export function useNotifications() {
  const context = useContext(NotificationsContext)
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationsProvider')
  }
  return context
}
