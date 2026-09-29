import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useGimbalStatus, useSetTrackingMode, useStopGimbal } from '../api/gimbal'
import { useMotorSpeeds } from '../api/motorSettings'
import { AxisInstrument } from '../components/manual/AxisInstrument'
import { MotorSpeedPanel } from '../components/status/MotorSpeedPanel'
import type { useDetectionSocket } from '../hooks/useDetectionSocket'

interface ManualModePageProps { detection: ReturnType<typeof useDetectionSocket> }

export function ManualModePage({ detection }: ManualModePageProps) {
  const { data: status, isError } = useGimbalStatus()
  const speeds = useMotorSpeeds()
  const tracking = useSetTrackingMode()
  const stop = useStopGimbal()
  const query = useQueryClient()
  const telemetry = status?.telemetry
  const online = !!status?.serial_connected && !isError
  const fresh = online && detection.connected
  const calibration = true // Manual control remains in pulses on both firmware modes.
  const trackingEnabled = status?.tracking_enabled ?? true
  const moving = telemetry?.moving ?? false
  const command = useMutation({
    mutationFn: async (input: { axis: 'pan' | 'tilt'; amount: number } | null) => {
      const result = input === null
        ? await api.post<{ ok: boolean }>('/api/gimbal/home')
        : calibration
          ? await api.post<{ ok: boolean }>('/api/gimbal/steps', { pan_steps: input.axis === 'pan' ? input.amount : 0, tilt_steps: input.axis === 'tilt' ? input.amount : 0 })
          : await api.post<{ ok: boolean }>('/api/gimbal/jog', { pan_deg: input.axis === 'pan' ? input.amount : 0, tilt_deg: input.axis === 'tilt' ? input.amount : 0 })
      if (!result.ok) throw new Error('No se confirmó la orden. Revisa la conexión y el contador antes de repetir: pudo haberse ejecutado.')
    },
    onSuccess: () => query.invalidateQueries({ queryKey: ['gimbal-status'] }),
  })
  const disabled = !fresh || !telemetry || trackingEnabled || moving || command.isPending || stop.isPending
  const error = command.error?.message ?? stop.error?.message ?? tracking.error?.message

  return (
    <div className="naval-console">
      <header className="naval-command-bar">
        <div><p className="naval-eyebrow">AI-RMY / CONTROL DE MOVIMIENTO</p><h1>Estación manual<span>CONTROL LOCAL</span></h1></div>
        <button className="naval-stop" onClick={() => stop.mutate()} disabled={stop.isPending}><span>■</span> {stop.isPending ? 'DETENIENDO…' : 'PARADA DE EMERGENCIA'}</button>
      </header>
      <div className="naval-status-strip">
        <span className={`naval-chip ${online ? 'is-online' : 'is-offline'}`}><i />{online ? 'CONTROLADOR CONECTADO' : 'CONTROLADOR SIN CONEXIÓN'}</span>
        <span>{telemetry?.calibration ? 'CALIBRACIÓN / PULSOS' : 'CONTROL / PULSOS'}</span>
        <span>{fresh ? 'TELEMETRÍA EN LÍNEA' : 'ESPERANDO TELEMETRÍA'}</span>
        <span className={trackingEnabled ? 'naval-warning' : ''}>AUTO {trackingEnabled ? 'ACTIVADO' : 'DESACTIVADO'}</span>
      </div>
      {trackingEnabled ? <div className="naval-notice"><span>Desactiva el seguimiento para tomar el control manual.</span><button onClick={() => tracking.mutate(false)} disabled={tracking.isPending}>Desactivar seguimiento</button></div> : null}
      {error ? <p role="alert" className="naval-error">{error}</p> : null}
      <div className="naval-section-heading"><span>01 — INSTRUMENTOS DE EJE</span><span>UN EJE POR ORDEN</span></div>
      <div className="naval-axis-grid">
        {(['pan', 'tilt'] as const).map(axis => <AxisInstrument key={axis} axis={axis} value={!fresh || !telemetry ? null : calibration ? telemetry[`${axis}_steps`] : telemetry[`${axis}_deg`]} calibration={calibration} disabled={disabled} moving={moving} speed={speeds.data?.manual[axis]} onMove={amount => command.mutate({ axis, amount })} />)}
      </div>
      <div className="naval-reference-bar">
        <div><strong>REFERENCIA RELATIVA · SIN ENCODER</strong><p>Los contadores registran pulsos emitidos, no el giro medido. Los diagramas identifican cada eje; no muestran su orientación real.{moving ? ' *El controlador informa movimiento del conjunto.' : ''}</p></div>
        <button disabled={disabled} onClick={() => command.mutate(null)}>↺ Poner ambos ejes a cero<span>Marca el origen sin mover</span></button>
      </div>
      <div className="naval-lower-grid">
        <section><div className="naval-section-heading"><span>02 — VELOCIDAD Y ACELERACIÓN</span></div><MotorSpeedPanel profile="manual" /></section>
        <aside className="naval-guide"><span className="naval-eyebrow">PROCEDIMIENTO DE CALIBRACIÓN</span><h3>Una referencia.<br />Un eje a la vez.</h3><ol><li>Marca el inicio y pon los contadores a cero.</li><li>Avanza por tramos. Reduce el incremento al acercarte a tu marca.</li><li>Anota el total de Pan antes de reiniciar para medir Tilt.</li></ol><p>Detente si el mecanismo o los cables limitan el recorrido.</p></aside>
      </div>
    </div>
  )
}
