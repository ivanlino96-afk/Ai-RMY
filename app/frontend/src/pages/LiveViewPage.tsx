import { useGimbalStatus } from '../api/gimbal'
import { CornerBracketPanel } from '../components/hud/CornerBracketPanel'
import { GimbalStatusPanel } from '../components/status/GimbalStatusPanel'
import { TrackedPersonPanel } from '../components/status/TrackedPersonPanel'
import { LiveVideoView } from '../components/video/LiveVideoView'
import type { useDetectionSocket } from '../hooks/useDetectionSocket'

interface LiveViewPageProps {
  detection: ReturnType<typeof useDetectionSocket>
}

export function LiveViewPage({ detection }: LiveViewPageProps) {
  const { data: status } = useGimbalStatus()
  const detections = detection.event?.detections ?? []

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <CornerBracketPanel
          title="Camera"
          color={detections.length > 0 ? 'lock' : 'hairline'}
          padded={false}
        >
          <LiveVideoView event={detection.event} />
        </CornerBracketPanel>
      </div>

      <div className="space-y-6">
        <TrackedPersonPanel detections={detections} />
        <GimbalStatusPanel status={status} />
      </div>
    </div>
  )
}
