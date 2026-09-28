import { useCameraList, useSelectCamera } from '../../api/camera'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'
import type { DetectionEvent } from '../../types/api'

interface CameraSelectPanelProps {
  event: DetectionEvent | null
}

export function CameraSelectPanel({ event }: CameraSelectPanelProps) {
  const { data, isFetching, refetch } = useCameraList()
  const selectCamera = useSelectCamera()
  const cameras = data?.cameras ?? []

  const selectedIndex = event?.camera_index ?? null
  const connected = event?.camera_connected ?? false

  const status = selectedIndex === null ? 'idle' : connected ? 'lock' : 'warn'
  const label = selectedIndex === null ? 'no camera selected' : connected ? 'live' : 'connecting'

  return (
    <CornerBracketPanel title="Camera Select" compact>
      <div className="space-y-1.5">
        <StatusBadge status={status} label={label} />

        <select
          value={selectedIndex ?? ''}
          onChange={(e) => selectCamera.mutate(Number(e.target.value))}
          disabled={selectCamera.isPending || cameras.length === 0}
          className="w-full border border-hairline bg-void px-3 py-1 text-xs tracking-[0.08em] text-ink uppercase disabled:opacity-40"
        >
          <option value="" disabled>
            {cameras.length === 0 ? 'no cameras found' : 'select a camera'}
          </option>
          {cameras.map((camera) => (
            <option key={camera.index} value={camera.index}>
              #{camera.index} — {camera.width}x{camera.height}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => refetch()}
          disabled={isFetching}
          className="w-full border border-hairline px-3 py-1 text-xs tracking-[0.1em] text-ink uppercase hover:border-lock hover:text-lock disabled:opacity-40"
        >
          {isFetching ? 'Scanning…' : 'Refresh'}
        </button>
      </div>
    </CornerBracketPanel>
  )
}
