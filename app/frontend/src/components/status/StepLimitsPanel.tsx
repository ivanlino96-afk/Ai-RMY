import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'

const keys = ['pan_min', 'pan_max', 'tilt_min', 'tilt_max'] as const
type Limits = Record<typeof keys[number], number>
export function StepLimitsPanel() {
  const cache = useQueryClient()
  const query = useQuery({ queryKey: ['step-limits'], queryFn: () => api.get<Limits>('/api/settings/step-limits') })
  const [draft, setDraft] = useState<Partial<Record<keyof Limits, string>>>({})
  const value = (key: keyof Limits) => draft[key] ?? String(query.data?.[key] ?? '')
  const values = Object.fromEntries(keys.map(key => [key, Number(value(key))])) as Limits
  const valid = keys.every(key => value(key).trim() !== '' && Number.isInteger(values[key]) && Math.abs(values[key]) <= 200000)
    && values.pan_min <= 0 && values.pan_max >= 0 && values.pan_min < values.pan_max
    && values.tilt_min <= 0 && values.tilt_max >= 0 && values.tilt_min < values.tilt_max
  const save = useMutation({ mutationFn: (limits: Limits) => api.post<Limits>('/api/settings/step-limits', limits), onSuccess: data => { cache.setQueryData(['step-limits'], data); setDraft({}) } })
  const dirty = query.data && keys.some(key => values[key] !== query.data?.[key])
  return <CornerBracketPanel title="Límites de recorrido · pasos">
    <form className="space-y-4" onSubmit={e => { e.preventDefault(); if (valid && dirty) save.mutate(values) }}>
      <p className="text-sm text-ink-dim">Posiciones acumuladas relativas al cero actual. Aplican al movimiento manual y al seguimiento automático con la transmisión calibrada.</p>
      <div className="grid gap-5 sm:grid-cols-2">
        {(['pan', 'tilt'] as const).map(axis => <fieldset key={axis} className="space-y-3 border border-hairline p-3">
          <legend className="px-2 text-sm text-ink uppercase">{axis}</legend>
          {(['min', 'max'] as const).map(bound => { const key = `${axis}_${bound}` as const; const label = bound === 'min' ? 'Mínimo' : 'Máximo'; return <label key={key} className="block space-y-1 text-sm text-ink">
            <span>{label} · pasos</span>
            <input aria-label={`${label} ${axis}`} type="number" min={-200000} max={200000} step={1} required value={value(key)} disabled={!query.data || save.isPending} onChange={e => { setDraft(d => ({...d, [key]: e.target.value})); save.reset() }} className="w-full border border-hairline bg-void px-3 py-2 text-base text-ink" />
          </label> })}
        </fieldset>)}
      </div>
      <p className="text-xs text-warn">Poner a cero o reiniciar el Arduino cambia la referencia física de estos límites. Sin encoder, la posición es un contador de pulsos, no una medición.</p>
      {!valid && query.data && <p role="alert" className="text-sm text-warn">Usa intervalos enteros que incluyan cero, con mínimo menor que máximo.</p>}
      {(query.isError || save.isError) && <p role="alert" className="text-sm text-danger">{(save.error ?? query.error)?.message ?? 'No se pudieron guardar los límites'}</p>}
      {save.isSuccess && <p role="status" className="text-sm text-accent">Límites guardados. Se aplican en la siguiente orden.</p>}
      <button type="submit" disabled={!valid || !dirty || save.isPending} className="border border-hairline px-4 py-2 text-sm text-ink disabled:opacity-40">{save.isPending ? 'Guardando…' : 'Guardar límites'}</button>
    </form>
  </CornerBracketPanel>
}
