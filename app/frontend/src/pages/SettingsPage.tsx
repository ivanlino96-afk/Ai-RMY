import { StepLimitsPanel } from '../components/status/StepLimitsPanel'
import { useGimbalStatus } from '../api/gimbal'
import { MotorSpeedPanel } from '../components/status/MotorSpeedPanel'

export function SettingsPage() {
  const { data: status } = useGimbalStatus()
  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-lg tracking-widest text-ink uppercase">Configuración de motores</h1>
        <p className="text-sm text-ink-dim">Ajusta por separado la velocidad y aceleración de Pan y Tilt para el seguimiento automático y el escaneo. Guardar no activa el seguimiento ni mueve los motores.</p>
        {status?.telemetry?.calibration ? <p className="border border-warn p-3 text-sm text-warn">Firmware de calibración activo: puedes guardar estos ajustes, pero el movimiento automático permanece bloqueado hasta volver al firmware normal.</p> : null}
      </div>
      <p className="border border-hairline p-3 text-sm text-ink-dim">Transmisión actual: Pan 12 000 pasos / 360° · Tilt 1500 pasos / ≈55°. Pan invertido y Tilt directo para seguimiento sobre imagen sin espejo. Ángulos estimados desde el origen.</p>
      <StepLimitsPanel />
      <MotorSpeedPanel profile="automatic" />
    </div>
  )
}
