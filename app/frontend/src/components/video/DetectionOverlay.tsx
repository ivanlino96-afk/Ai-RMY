import type { DetectionEvent } from '../../types/api'
import { UNKNOWN_LABEL } from '../../constants'

interface DetectionOverlayProps {
  event: DetectionEvent | null
}

// Positions are percentages derived from the event's own frame_width/height,
// so the overlay lines up with the stream regardless of the camera's
// configured resolution (see vision/config.py CameraConfig).
export function DetectionOverlay({ event }: DetectionOverlayProps) {
  const detection = event?.detection ?? null
  const locked = detection !== null && detection.label !== null && detection.label !== UNKNOWN_LABEL

  return (
    <div className="pointer-events-none absolute inset-0">
      <div className="absolute inset-y-0 left-1/2 w-px bg-ink/10" />
      <div className="absolute inset-x-0 top-1/2 h-px bg-ink/10" />

      {detection && event ? (
        <div
          className={`absolute border-2 ${locked ? 'border-lock animate-lock-pulse' : 'border-warn'}`}
          style={{
            left: `${(detection.bbox[0] / event.frame_width) * 100}%`,
            top: `${(detection.bbox[1] / event.frame_height) * 100}%`,
            width: `${(detection.bbox[2] / event.frame_width) * 100}%`,
            height: `${(detection.bbox[3] / event.frame_height) * 100}%`,
          }}
        >
          <span
            className={`absolute -top-6 left-0 whitespace-nowrap px-1 text-xs tracking-[0.08em] ${
              locked ? 'bg-lock text-void' : 'bg-warn text-void'
            }`}
          >
            {(detection.label ?? UNKNOWN_LABEL).toUpperCase()} ({Math.round(detection.score * 100)}%)
          </span>
        </div>
      ) : null}
    </div>
  )
}
