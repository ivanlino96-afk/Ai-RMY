import type { ReactNode } from 'react'
import { useDetectionSocket } from '../../hooks/useDetectionSocket'
import { TopBar } from './TopBar'

interface AppShellProps {
  children: (detection: ReturnType<typeof useDetectionSocket>) => ReactNode
}

// The WebSocket connection lives here, once, and is threaded down to
// whichever page needs live detection/telemetry events — pages don't each
// open their own socket.
export function AppShell({ children }: AppShellProps) {
  const detection = useDetectionSocket()

  return (
    <div className="min-h-screen bg-void">
      <TopBar
        serialConnected={detection.event?.serial_connected ?? false}
        socketConnected={detection.connected}
      />
      <main className="mx-auto max-w-6xl px-6 py-6">{children(detection)}</main>
    </div>
  )
}
