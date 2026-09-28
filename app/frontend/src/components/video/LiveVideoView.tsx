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
    </div>
  )
}
