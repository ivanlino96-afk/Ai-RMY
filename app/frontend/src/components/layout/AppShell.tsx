import type { ReactNode } from 'react'
import { useEffect, useRef } from 'react'
import { useDetectionSocket } from '../../hooks/useDetectionSocket'
import { lastCameraIndex } from '../../hooks/useCameraOwner'
import { useNotifications } from '../../hooks/useNotifications'
import { TopBar } from './TopBar'

interface AppShellProps {
  children: (detection: ReturnType<typeof useDetectionSocket>) => ReactNode
}

// The WebSocket connection lives here, once, and is threaded down to
// whichever page needs live detection/telemetry events — pages don't each
// open their own socket.
export function AppShell({ children }: AppShellProps) {
  const detection = useDetectionSocket()
  const { notify } = useNotifications()
  const lastCameraConnected = useRef<boolean | null>(null)

  // RF-16: every disconnect/reconnect transition gets its own notification,
  // not just the first one — so this watches for a *change*, not a state.
  useEffect(() => {
    const current = detection.event?.camera_connected
    if (current === undefined) return
    if (lastCameraConnected.current !== null && lastCameraConnected.current !== current) {
      notify(current ? 'Camera reconnected.' : 'Camera disconnected.', current ? 'info' : 'alert')
    }
    lastCameraConnected.current = current
  }, [detection.event?.camera_connected, notify])

  useEffect(() => {
    if (detection.event?.camera_index != null) {
      lastCameraIndex.current = detection.event.camera_index
    }
  }, [detection.event?.camera_index])

  return (
    <div className="flex h-screen flex-col bg-void">
      <TopBar
        serialConnected={detection.event?.serial_connected ?? false}
        socketConnected={detection.connected}
      />
      <main className="mx-auto w-full min-h-0 max-w-[1600px] flex-1 overflow-y-auto px-6 py-4">
        {children(detection)}
      </main>
    </div>
  )
}
