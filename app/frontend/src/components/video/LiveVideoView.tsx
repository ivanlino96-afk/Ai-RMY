import type { DetectionEvent } from '../../types/api'
import { DetectionOverlay } from './DetectionOverlay'

interface LiveVideoViewProps {
  event: DetectionEvent | null
}

// The video element needs no React state of its own — the browser decodes
// the MJPEG multipart stream directly from app/backend's /api/stream/video.
// Only the overlay (reticle + bbox) is driven by the WebSocket event.
export function LiveVideoView({ event }: LiveVideoViewProps) {
  return (
    <div className="relative aspect-video w-full overflow-hidden bg-black">
      <img
        src="/api/stream/video"
        alt="Live camera feed"
        className="h-full w-full object-cover"
      />
      <DetectionOverlay event={event} />
    </div>
  )
}
