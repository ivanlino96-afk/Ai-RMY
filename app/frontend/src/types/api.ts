// Mirrors app/backend/schemas.py — keep both in sync when either changes.

export interface Person {
  id: number
  name: string
  notes: string
  created_at: number
}

export interface Detection {
  bbox: [number, number, number, number]
  score: number
  label: string | null
}

export interface Telemetry {
  ok: boolean
  pan_deg: number
  tilt_deg: number
  moving: boolean
  homed: boolean
}

export interface DetectionEvent {
  frame_width: number
  frame_height: number
  detection: Detection | null
  telemetry: Telemetry | null
  serial_connected: boolean
  tracking_enabled: boolean
}

export interface GimbalStatus {
  serial_connected: boolean
  tracking_enabled: boolean
  telemetry: Telemetry | null
}

export interface Health {
  status: string
  version: string
}
