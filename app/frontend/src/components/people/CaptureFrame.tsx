import { useRef } from 'react'
import { useDetectionSocket } from '../../hooks/useDetectionSocket'
import { bboxToStyle } from '../video/bboxStyle'

interface CaptureFrameProps {
  onCapture: (photo: Blob) => void
  disabled?: boolean
}

// RF-2: shows a live encuadre (reticle) over the detected face so the user
// can position themselves before taking each of the 3 guided photos. This
// is purely a positioning aid — it reuses the same live pipeline detections
// as the Live View page, not a separate detection run; the backend's own
// exactly-one-face check on submit (RF-4) is what's actually authoritative.
export function CaptureFrame({ onCapture, disabled }: CaptureFrameProps) {
  const imgRef = useRef<HTMLImageElement>(null)
  const { event } = useDetectionSocket()
  const detections = event?.detections ?? []
  const ready = detections.length === 1

  const capture = () => {
    const img = imgRef.current
    if (!img || !img.naturalWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(img, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob)
      },
      'image/jpeg',
      0.92,
    )
  }

  return (
    <div className="space-y-2">
      <div className="relative aspect-video w-full overflow-hidden border border-hairline bg-black">
        <img ref={imgRef} src="/api/stream/video" alt="Camera preview" className="h-full w-full object-cover" />
        {ready && event?.frame_width && event?.frame_height ? (
          <div
            className="pointer-events-none absolute border-2 border-lock"
            style={bboxToStyle(detections[0].bbox, event.frame_width, event.frame_height)}
          />
        ) : null}
      </div>

      <p className="text-xs text-warn">
        {detections.length === 0
          ? 'Position your face in the frame.'
          : detections.length > 1
            ? 'Only one face should be visible.'
            : ' '}
      </p>

      <button
        type="button"
        onClick={capture}
        disabled={disabled || !ready}
        className="w-full border border-hairline px-3 py-2 text-xs uppercase tracking-[0.1em] text-lock hover:border-lock disabled:opacity-40"
      >
        Capture
      </button>
    </div>
  )
}
