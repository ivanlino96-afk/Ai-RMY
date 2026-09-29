import { useEffect, useRef } from 'react'
import { useDefenseStatus } from '../api/defense'
import { useGimbalStatus } from '../api/gimbal'
import { CornerBracketPanel } from '../components/hud/CornerBracketPanel'
import { CameraSelectPanel } from '../components/status/CameraSelectPanel'
import { DefenseLogPanel } from '../components/status/DefenseLogPanel'
import { DefenseModePanel } from '../components/status/DefenseModePanel'
import { TrackingModePanel } from '../components/status/TrackingModePanel'
import { GimbalStatusPanel } from '../components/status/GimbalStatusPanel'
import { TrackedPersonPanel } from '../components/status/TrackedPersonPanel'
import { TrackingOffsetPanel } from '../components/status/TrackingOffsetPanel'
import { LiveTrackingRadar } from '../components/video/LiveTrackingRadar'
import { LiveVideoView } from '../components/video/LiveVideoView'
import { useCameraOwner } from '../hooks/useCameraOwner'
import { useNotifications } from '../hooks/useNotifications'
import type { useDetectionSocket } from '../hooks/useDetectionSocket'

interface LiveViewPageProps {
  detection: ReturnType<typeof useDetectionSocket>
}

const RECENT_THREAT_WINDOW_S = 5

// Lazily created so the first beep only ever happens after the page has
// already seen some user interaction (arming the alarm, clicking a nav
// link, etc.) -- browsers refuse to start an AudioContext with zero prior
// gesture, and this sidesteps that without needing to wire a "click to
// enable sound" prompt of its own.
let alarmAudioContext: AudioContext | null = null

function playAlarmBeep() {
  try {
    if (!alarmAudioContext) {
      alarmAudioContext = new AudioContext()
    }
    const ctx = alarmAudioContext
    const oscillator = ctx.createOscillator()
    const gain = ctx.createGain()
    oscillator.type = 'square'
    oscillator.frequency.value = 880
    gain.gain.setValueAtTime(0.15, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)
    oscillator.connect(gain)
    gain.connect(ctx.destination)
    oscillator.start()
    oscillator.stop(ctx.currentTime + 0.4)
  } catch {
    // Autoplay restrictions or an unsupported browser -- the visual alert
    // (toast + full-screen border) still gets through either way.
  }
}

export function LiveViewPage({ detection }: LiveViewPageProps) {
  useCameraOwner()
  const { notify } = useNotifications()
  const { data: status } = useGimbalStatus()
  const defenseStatusQuery = useDefenseStatus()
  const detections = detection.event?.detections ?? []
  const defenseStatus = detection.event?.defense ?? defenseStatusQuery.data ?? null
  const defenseLog = defenseStatus?.log ?? []
  const lastThreatCount = useRef(0)

  useEffect(() => {
    const threatCount = defenseLog.filter((entry) => entry.type === 'threat').length
    if (threatCount > lastThreatCount.current) {
      notify('Threat detected: unrecognized subject', 'alert')
      playAlarmBeep()
    }
    lastThreatCount.current = threatCount
  }, [defenseLog, notify])

  const lastThreatTimestamp = defenseLog
    .filter((entry) => entry.type === 'threat')
    .reduce((latest, entry) => Math.max(latest, entry.timestamp), 0)
  const hasRecentThreat = Date.now() / 1000 - lastThreatTimestamp < RECENT_THREAT_WINDOW_S
  const showFullScreenAlert = (defenseStatus?.active ?? false) && hasRecentThreat

  return (
    <div className="space-y-6 lg:flex lg:h-full lg:flex-col lg:gap-3 lg:space-y-0">
      {showFullScreenAlert ? (
        <div className="pointer-events-none fixed inset-0 z-50 border-4 border-alert animate-lock-pulse" />
      ) : null}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4 lg:flex-1 lg:min-h-0 lg:items-stretch lg:gap-3 lg:grid-rows-[minmax(0,1fr)]">
        <div className="lg:col-span-3 lg:h-full lg:min-h-0">
          <CornerBracketPanel
            title="Camera"
            color={detections.length > 0 ? 'lock' : 'hairline'}
            padded={false}
            className="lg:flex lg:h-full lg:min-h-0 lg:flex-col"
          >
            <div className="lg:min-h-0 lg:flex-1">
              <LiveVideoView event={detection.event} />
            </div>
          </CornerBracketPanel>
        </div>

        <div className="space-y-6 lg:col-span-1 lg:h-full lg:min-h-0 lg:space-y-1.5 lg:overflow-y-auto lg:pr-1">
          <TrackingModePanel status={status} />
          <CameraSelectPanel event={detection.event} />
          <TrackingOffsetPanel
            offset={detection.event?.tracking_offset ?? null}
            frameWidth={detection.event?.frame_width ?? null}
            frameHeight={detection.event?.frame_height ?? null}
          />
          <GimbalStatusPanel status={status} />
          <DefenseModePanel status={defenseStatus} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:h-48 lg:flex-none lg:min-h-0 lg:items-stretch lg:gap-3 lg:grid-rows-[minmax(0,1fr)]">
        <TrackedPersonPanel detections={detections} />
        <DefenseLogPanel log={defenseLog} />
        <LiveTrackingRadar
          detections={detections}
          frameWidth={detection.event?.frame_width ?? null}
          frameHeight={detection.event?.frame_height ?? null}
          armed={defenseStatus?.active ?? false}
        />
      </div>
    </div>
  )
}
