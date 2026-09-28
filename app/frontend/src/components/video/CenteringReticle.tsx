import type { DetectionEvent } from '../../types/api'
import { useHeldTrue } from '../../hooks/useHeldTrue'
import { centerBoxStyle } from './bboxStyle'

interface CenteringReticleProps {
  event: DetectionEvent | null
}

// Distinct from DetectionOverlay's per-face recognition box: this one tracks
// how far the primary target still is from frame-center, and turns green
// with "FIXED" once it's stayed centered continuously for 3s. Purely a
// renderer over event.tracking_offset -- no geometry is recomputed here
// (see vision/pipeline.py's _process_frame for where dx/dy/centered come
// from), the 3s hold is pure UI timing (useHeldTrue).
export function CenteringReticle({ event }: CenteringReticleProps) {
  const offset = event?.tracking_offset ?? null
  const frameWidth = event?.frame_width
  const frameHeight = event?.frame_height
  const target = event?.detections?.[0] ?? null

  const fixed = useHeldTrue(offset?.centered ?? false, 3000)

  if (!offset || !target || !frameWidth || !frameHeight) {
    return null
  }

  const distance = Math.round(Math.hypot(offset.dx, offset.dy))

  return (
    <div
      className={`pointer-events-none absolute border-2 border-dashed ${
        fixed ? 'border-lock animate-lock-pulse' : 'border-warn'
      }`}
      style={centerBoxStyle(target.bbox, 0.16, frameWidth, frameHeight)}
    >
      <span
        className={`absolute -bottom-6 left-0 whitespace-nowrap px-1 text-xs tracking-[0.08em] ${
          fixed ? 'bg-lock text-void' : 'bg-warn text-void'
        }`}
      >
        {fixed ? 'FIXED' : `Δ${distance}px`}
      </span>
    </div>
  )
}
