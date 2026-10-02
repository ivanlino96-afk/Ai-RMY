import { StepLimitsPanel } from '../components/status/StepLimitsPanel'
import { useGimbalStatus } from '../api/gimbal'
import { MotorSpeedPanel } from '../components/status/MotorSpeedPanel'
import { PageHeader } from '../components/hud/PageHeader'

export function SettingsPage() {
  const { data: status } = useGimbalStatus()
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader code="SYS-05" title="Configuración de motores" />
      <div className="space-y-2">
        <p className="text-sm text-ink-dim">Ajusta por separado la velocidad y aceleración de Pan y Tilt para el seguimiento automático y el escaneo. Guardar no activa el seguimiento ni mueve los motores.</p>
        {status?.telemetry?.calibration ? <p className="border border-warn p-3 text-sm text-warn">Firmware de calibración activo: puedes guardar estos ajustes, pero el movimiento automático permanece bloqueado hasta volver al firmware normal.</p> : null}
      </div>
      <p className="border border-hairline p-3 text-sm text-ink-dim">Transmisión actual: Pan 12 000 pasos / 360° · Tilt 1500 pasos / ≈55°. Pan invertido y Tilt directo para seguimiento sobre imagen sin espejo. Ángulos estimados desde el origen.</p>
      <StepLimitsPanel />
      <MotorSpeedPanel profile="automatic" />
    </div>
  )
}
