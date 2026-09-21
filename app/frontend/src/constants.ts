import type { Pose } from './types/api'

// Mirrors vision.pipeline.UNKNOWN_LABEL.
export const UNKNOWN_LABEL = 'Desconocido'

// Mirrors vision.enroll.POSE_ORDER.
export const POSE_ORDER: readonly Pose[] = ['front', 'left', 'right']

export const POSE_LABELS: Record<Pose, string> = {
  front: 'Face forward',
  left: 'Turn slightly left',
  right: 'Turn slightly right',
}
