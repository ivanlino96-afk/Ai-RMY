import { useGimbalStatus, useSetTrackingMode } from '../api/gimbal'
import { useCancelScan, useScanStatus, useStartScan } from '../api/scan'
import { CornerBracketPanel } from '../components/hud/CornerBracketPanel'
import { ScanControlPanel } from '../components/status/ScanControlPanel'
import { ScanRadarView } from '../components/video/ScanRadarView'
import { useCameraOwner } from '../hooks/useCameraOwner'
import type { useDetectionSocket } from '../hooks/useDetectionSocket'

interface RoomScanPageProps {
  detection: ReturnType<typeof useDetectionSocket>
}

const PAN_RANGE_DEG: [number, number] = [-45, 45]
const TILT_RANGE_DEG: [number, number] = [-30, 30]

// Manual scan, no persisted history (confirmed scope): each scan replaces
// the previous result in memory, nothing is written to SQLite. Live
// progress rides the existing detection WebSocket event (event.scan) --
// useScanStatus() only covers the gap before the first event arrives.
export function RoomScanPage({ detection }: RoomScanPageProps) {
  useCameraOwner()
  const { data: gimbalStatus } = useGimbalStatus()
  const { data: polledStatus } = useScanStatus()
  const setTrackingMode = useSetTrackingMode()
  const startScan = useStartScan()
  const cancelScan = useCancelScan()

  const scan = detection.event?.scan ?? polledStatus ?? { state: 'idle' as const, progress: 0, results: [] }
  const trackingEnabled = gimbalStatus?.tracking_enabled ?? true

  return (
    <div className="space-y-6">
      {trackingEnabled ? (
        <CornerBracketPanel color="warn">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-warn">
              Tracking is active — disable it before starting a room scan, so the
              auto-tracker doesn't fight the scan's own gimbal moves.
            </p>
            <button
              type="button"
              onClick={() => setTrackingMode.mutate(false)}
              disabled={setTrackingMode.isPending}
              className="border border-hairline px-3 py-2 text-xs tracking-[0.1em] text-ink uppercase hover:border-warn hover:text-warn disabled:opacity-40"
            >
              Disable tracking
            </button>
          </div>
        </CornerBracketPanel>
      ) : null}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,320px)_1fr]">
        <ScanControlPanel
          trackingEnabled={trackingEnabled}
          scanState={scan.state}
          progress={scan.progress}
          resultCount={scan.results.length}
          startPending={startScan.isPending}
          cancelPending={cancelScan.isPending}
          onStart={() =>
            startScan.mutate({
              pan_range_deg: PAN_RANGE_DEG,
              tilt_range_deg: TILT_RANGE_DEG,
            })
          }
          onCancel={() => cancelScan.mutate()}
        />
        <ScanRadarView results={scan.results} panRangeDeg={PAN_RANGE_DEG} tiltRangeDeg={TILT_RANGE_DEG} />
      </div>
    </div>
  )
}
