import type { DetectionEvent } from '../../types/api'
import { CenteringReticle } from './CenteringReticle'
import { DetectionOverlay } from './DetectionOverlay'

interface LiveVideoViewProps {
  event: DetectionEvent | null
}

// The video element needs no React state of its own — the browser decodes
// the MJPEG multipart stream directly from app/backend's /api/stream/video.
// Only the overlays (reticle + bbox) are driven by the WebSocket event.
export function LiveVideoView({ event }: LiveVideoViewProps) {
  return (
    <div className="relative aspect-video w-full overflow-hidden bg-black lg:aspect-auto lg:h-full">
      <img
        src="/api/stream/video"
        alt="Live camera feed"
        className="h-full w-full object-cover"
      />
      <DetectionOverlay event={event} />
      <CenteringReticle event={event} />
      <div
        aria-hidden="true"
        className="animate-scan pointer-events-none absolute inset-x-0 h-1/3 bg-linear-to-b from-transparent via-lock/10 to-transparent"
      />
    </div>
  )
}
