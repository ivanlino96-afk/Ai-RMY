import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useGimbalStatus, useSetTrackingMode, useStopGimbal } from '../api/gimbal'
import { useMotorSpeeds } from '../api/motorSettings'
import { AxisInstrument } from '../components/manual/AxisInstrument'
import { PageHeader } from '../components/hud/PageHeader'
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
    <div className="pb-6">
      <PageHeader
        code="SYS-03"
        title="Estación manual"
        subtitle="CONTROL LOCAL"
        action={
          <button
            className="shrink-0 border border-alert bg-alert/10 px-4 py-3 text-xs text-alert hover:bg-alert/20 disabled:opacity-40"
            onClick={() => stop.mutate()}
            disabled={stop.isPending}
          >
            ■ {stop.isPending ? 'DETENIENDO…' : 'PARADA DE EMERGENCIA'}
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-x-7 gap-y-3 border-b border-hairline pb-4 font-mono text-[10px] normal-case tracking-[0.1em] text-ink-dim">
        <span className={`inline-flex items-center gap-2 ${online ? 'text-lock' : 'text-alert'}`}>
          <i className={`h-1.5 w-1.5 ${online ? 'bg-lock' : 'bg-alert'}`} />
          {online ? 'CONTROLADOR CONECTADO' : 'CONTROLADOR SIN CONEXIÓN'}
        </span>
        <span>{telemetry?.calibration ? 'CALIBRACIÓN / PULSOS' : 'CONTROL / PULSOS'}</span>
        <span>{fresh ? 'TELEMETRÍA EN LÍNEA' : 'ESPERANDO TELEMETRÍA'}</span>
        <span className={trackingEnabled ? 'text-warn' : ''}>AUTO {trackingEnabled ? 'ACTIVADO' : 'DESACTIVADO'}</span>
      </div>

      {trackingEnabled ? (
        <div className="mt-4 flex items-center justify-between gap-3 border border-warn/50 bg-warn/10 p-3 text-sm normal-case text-warn">
          <span>Desactiva el seguimiento para tomar el control manual.</span>
          <button className="shrink-0 border border-warn px-3 py-2 text-xs disabled:opacity-40" onClick={() => tracking.mutate(false)} disabled={tracking.isPending}>
            Desactivar seguimiento
          </button>
        </div>
      ) : null}
      {error ? <p role="alert" className="mt-4 text-sm normal-case text-alert">{error}</p> : null}

      <div className="mt-6 flex items-center justify-between">
        <p className="field-label">01 — Instrumentos de eje</p>
        <p className="field-label">Un eje por orden</p>
      </div>
      <div className="mt-2 grid gap-4 md:grid-cols-2">
        {(['pan', 'tilt'] as const).map(axis => <AxisInstrument key={axis} axis={axis} value={!fresh || !telemetry ? null : calibration ? telemetry[`${axis}_steps`] : telemetry[`${axis}_deg`]} calibration={calibration} disabled={disabled} moving={moving} speed={speeds.data?.manual[axis]} onMove={amount => command.mutate({ axis, amount })} />)}
      </div>

      <div className="mt-4 flex items-center justify-between gap-5 border border-hairline bg-panel p-4">
        <div>
          <p className="field-label text-ink">Referencia relativa · sin encoder</p>
          <p className="mt-1 max-w-2xl text-xs normal-case leading-relaxed text-ink-dim">
            Los contadores registran pulsos emitidos, no el giro medido. Los diagramas identifican cada eje; no muestran su orientación real.
            {moving ? ' *El controlador informa movimiento del conjunto.' : ''}
          </p>
        </div>
        <button disabled={disabled} onClick={() => command.mutate(null)} className="shrink-0 border border-hairline px-3 py-2 text-xs text-ink disabled:opacity-40">
          ↺ Poner ambos ejes a cero
          <span className="mt-1 block font-mono text-[9px] normal-case text-ink-dim">Marca el origen sin mover</span>
        </button>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <section>
          <p className="field-label mb-2">02 — Velocidad y aceleración</p>
          <MotorSpeedPanel profile="manual" />
        </section>
        <aside className="border-l border-hairline pl-6">
          <p className="field-label">Procedimiento de calibración</p>
          <h3 className="mt-2 text-xl normal-case leading-snug text-ink">Una referencia.<br />Un eje a la vez.</h3>
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-xs normal-case leading-relaxed text-ink-dim">
            <li>Marca el inicio y pon los contadores a cero.</li>
            <li>Avanza por tramos. Reduce el incremento al acercarte a tu marca.</li>
            <li>Anota el total de Pan antes de reiniciar para medir Tilt.</li>
          </ol>
          <p className="mt-4 text-xs normal-case text-warn">Detente si el mecanismo o los cables limitan el recorrido.</p>
        </aside>
      </div>
    </div>
  )
}
