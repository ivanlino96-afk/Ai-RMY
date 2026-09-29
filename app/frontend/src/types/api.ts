// Mirrors app/backend/schemas.py — keep both in sync when either changes.

export interface Person {
  id: number
  name: string
  age: number | null
  email: string
  phone: string
  notes: string
  created_at: number
}

export interface PersonInput {
  name: string
  age?: number | null
  email?: string
  phone?: string
  notes?: string
}

export interface Detection {
  bbox: [number, number, number, number]
  score: number
  label: string | null
}

export interface Telemetry {
  calibration: boolean
  pan_steps: number
  tilt_steps: number
  ok: boolean
  pan_deg: number
  tilt_deg: number
  moving: boolean
  homed: boolean
}

export interface TrackingOffset {
  dx: number
  dy: number
  pan_deg: number
  tilt_deg: number
  centered: boolean
}

export interface ScanObject {
  bbox: [number, number, number, number]
  label: string
  score: number
}

export interface ScanWaypoint {
  pan_deg: number
  tilt_deg: number
  objects: ScanObject[]
}

export interface ScanStatus {
  state: 'idle' | 'running' | 'done'
  progress: number
  results: ScanWaypoint[]
}

export interface ScanConfigInput {
  pan_range_deg?: [number, number]
  tilt_range_deg?: [number, number]
  step_deg?: number
}

export interface DefenseLogEntry {
  type: 'identified' | 'threat'
  timestamp: number
  name: string | null
  photo: string | null
}

export interface DefenseStatus {
  active: boolean
  armed_at: number | null
  log: DefenseLogEntry[]
}

export interface DetectionEvent {
  frame_width: number | null
  frame_height: number | null
  detections: Detection[]
  telemetry: Telemetry | null
  serial_connected: boolean
  tracking_enabled: boolean
  camera_connected: boolean
  camera_index: number | null
  tracking_offset: TrackingOffset | null
  scan: ScanStatus | null
  defense: DefenseStatus | null
}

export interface CameraInfo {
  index: number
  width: number
  height: number
}

export interface CameraList {
  cameras: CameraInfo[]
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

// Mirrors vision.enroll.POSE_ORDER.
export type Pose = 'front' | 'left' | 'right'

export interface EnrollmentSessionStart {
  session_id: string
  next_pose: Pose
}

export interface EnrollmentPhotoResult {
  pose: Pose
  next_pose: Pose | null
  is_complete: boolean
}
