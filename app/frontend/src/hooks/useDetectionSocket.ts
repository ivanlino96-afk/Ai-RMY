import { useEffect, useRef, useState } from 'react'
import type { DetectionEvent } from '../types/api'

// Reconnects with a fixed short backoff — the pipeline event stream is a
// live operating view, not a critical control path (the ESP32 remains the
// authority over motor limits regardless of this socket's state).
const RECONNECT_DELAY_MS = 1500

export function useDetectionSocket() {
  const [event, setEvent] = useState<DetectionEvent | null>(null)
  const [connected, setConnected] = useState(false)
  const closedByUnmount = useRef(false)

  useEffect(() => {
    closedByUnmount.current = false
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      socket = new WebSocket(`${protocol}://${window.location.host}/api/ws/events`)

      socket.onopen = () => setConnected(true)
      socket.onmessage = (message) => {
        setEvent(JSON.parse(message.data) as DetectionEvent)
      }
      socket.onclose = () => {
        setConnected(false)
        if (!closedByUnmount.current) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS)
        }
      }
      socket.onerror = () => socket?.close()
    }

    connect()

    return () => {
      closedByUnmount.current = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  return { event, connected }
}
