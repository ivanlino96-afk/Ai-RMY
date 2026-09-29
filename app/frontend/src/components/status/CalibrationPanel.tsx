import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { GimbalStatus } from '../../types/api'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'

export function CalibrationPanel({ status }: { status: GimbalStatus | undefined }) {
  const [amount, setAmount] = useState('20')
  const query = useQueryClient()
  const command = useMutation({
    mutationFn: async (payload: { pan_steps: number; tilt_steps: number } | null) => {
      const result = payload === null
        ? await api.post<{ ok: boolean }>('/api/gimbal/home')
        : await api.post<{ ok: boolean }>('/api/gimbal/steps', payload)
      if (!result.ok) throw new Error('Orden rechazada. Comprueba conexión, seguimiento y movimiento pendiente.')
    },
    onSuccess: () => query.invalidateQueries({ queryKey: ['gimbal-status'] }),
  })
  const steps = Number(amount)
  const ready = status?.telemetry?.calibration && status.serial_connected && !status.tracking_enabled
  const disabled = !ready || status?.telemetry?.moving || command.isPending
  const invalid = !Number.isInteger(steps) || steps < 1 || steps > 2000

  return (
    <CornerBracketPanel title="Calibración por pasos">
      <div className="space-y-4">
        <p className="text-sm text-ink-dim">Cada paso es un pulso STEP. Marca el inicio en el mecanismo y avanza en tramos hasta completar una vuelta. Los contadores no detectan pasos perdidos.</p>
        {!ready ? <p className="text-warn">Requiere firmware de calibración conectado y seguimiento desactivado.</p> : null}
        <label className="flex items-center gap-3 text-sm text-ink">
          Pasos por orden (1–2000)
          <input aria-label="Pasos por orden" type="number" min="1" max="2000" step="1" value={amount} onChange={e => setAmount(e.target.value)} className="w-24 border border-hairline bg-void p-2" />
        </label>
        <div className="grid gap-4 md:grid-cols-2">
          {(['pan', 'tilt'] as const).map(axis => (
            <div key={axis} className="space-y-3 border border-hairline p-4">
              <p className="text-ink uppercase">{axis}: <strong>{status?.telemetry?.[`${axis}_steps`] ?? '—'}</strong> pulsos desde cero</p>
              <div className="flex gap-3">
                {([-1, 1] as const).map(sign => <button key={sign} disabled={disabled || invalid} onClick={() => command.mutate({ pan_steps: axis === 'pan' ? sign * steps : 0, tilt_steps: axis === 'tilt' ? sign * steps : 0 })} className="flex-1 border border-lock p-3 text-lock disabled:opacity-40">{sign < 0 ? '−' : '+'} {axis}</button>)}
              </div>
            </div>
          ))}
        </div>
        <button disabled={disabled} onClick={() => command.mutate(null)} className="border border-hairline p-3 text-ink disabled:opacity-40">Poner ambos contadores a cero (sin mover)</button>
        <p className="text-xs text-ink-dim">Anota el total de Pan antes de poner a cero para medir Tilt. No fuerces una vuelta si los cables o el mecanismo no lo permiten.</p>
        {command.isError ? <p role="alert" className="text-alert">{command.error.message}</p> : null}
      </div>
    </CornerBracketPanel>
  )
}
