import type { DetectionEvent } from '../../types/api'
import { UNKNOWN_LABEL } from '../../constants'
import { bboxToStyle } from './bboxStyle'

interface DetectionOverlayProps {
  event: DetectionEvent | null
}

// One box per detection (RF-11): green+name for a >=90% match, red+
// "Desconocido" otherwise (RF-12, RF-13). Purely a renderer — the event's
// own `detections` array already carries the matched/unmatched decision
// (vision/pipeline.py), nothing is recomputed here.
export function DetectionOverlay({ event }: DetectionOverlayProps) {
  const detections = event?.detections ?? []
  const frameWidth = event?.frame_width
  const frameHeight = event?.frame_height

  return (
    <div className="pointer-events-none absolute inset-0">
      <div className="absolute inset-y-0 left-1/2 w-px bg-ink/10" />
      <div className="absolute inset-x-0 top-1/2 h-px bg-ink/10" />

      {frameWidth && frameHeight
        ? detections.map((detection, index) => {
            const locked = detection.label !== null && detection.label !== UNKNOWN_LABEL
            return (
              <div
                key={index}
                className={`absolute border-2 ${locked ? 'border-lock animate-lock-pulse' : 'border-alert'}`}
                style={bboxToStyle(detection.bbox, frameWidth, frameHeight)}
              >
                <span
                  className={`absolute -top-6 left-0 whitespace-nowrap px-1 text-xs tracking-[0.08em] ${
                    locked ? 'bg-lock text-void' : 'bg-alert text-void'
                  }`}
                >
                  {(detection.label ?? UNKNOWN_LABEL).toUpperCase()} ({Math.round(detection.score * 100)}%)
                </span>
              </div>
            )
          })
        : null}
    </div>
  )
}
