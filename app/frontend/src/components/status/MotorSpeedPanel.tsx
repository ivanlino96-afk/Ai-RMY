import { useState } from 'react'
import { useMotorSpeeds, useSaveMotorSpeeds, type SpeedProfile, type MotorSpeeds } from '../../api/motorSettings'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'

const keys = ['pan', 'tilt', 'pan_acceleration', 'tilt_acceleration'] as const
export function MotorSpeedPanel({ profile }: { profile: SpeedProfile }) {
  const settings = useMotorSpeeds()
  const save = useSaveMotorSpeeds(profile)
  const [draft, setDraft] = useState<Partial<Record<keyof MotorSpeeds, string>>>({})
  const current = settings.data?.[profile]
  const value = (key: keyof MotorSpeeds) => draft[key] ?? String(current?.[key] ?? '')
  const valid = keys.every(key => { const v = value(key); return v.trim() !== '' && Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= (key.endsWith('_acceleration') ? 20000 : 4000) })
  const dirty = current && keys.some(key => Number(value(key)) !== current[key])
  const profileName = profile === 'manual' ? 'manual' : 'automática'
  return (
    <CornerBracketPanel title={profile === 'manual' ? 'Movimiento manual' : 'Movimiento automático'}>
      <form className="space-y-4" onSubmit={event => {
        event.preventDefault()
        if (valid && current && !save.isPending) save.mutate({ pan: Number(value('pan')), tilt: Number(value('tilt')), pan_acceleration: Number(value('pan_acceleration')), tilt_acceleration: Number(value('tilt_acceleration')) }, { onSuccess: () => setDraft({}) })
      }}>
        <p className="text-sm text-ink-dim">Ajustes independientes por eje. Se guardan al reiniciar y se aplican en la siguiente orden; guardar no mueve los motores.</p>
        <div className="grid gap-5 sm:grid-cols-2">
          {(['pan', 'tilt'] as const).map(axis => <fieldset key={axis} className="space-y-3 border border-hairline p-3">
            <legend className="px-2 text-sm text-ink uppercase">{axis}</legend>
            {([false, true] as const).map(acceleration => {
              const key = acceleration ? `${axis}_acceleration` as const : axis
              const label = acceleration ? 'Aceleración' : 'Velocidad máxima'
              return <label key={key} className="block space-y-1 text-xs text-ink">
                <span className="block">{label} · {acceleration ? 'pulsos/s²' : 'pulsos/s'}</span>
                <input aria-label={`${acceleration ? 'Aceleración' : 'Velocidad'} ${profileName} ${axis}`} type="number" min="1" max={acceleration ? 20000 : 4000} step="1" required disabled={!current || save.isPending} value={value(key)} onChange={e => { setDraft(previous => ({ ...previous, [key]: e.target.value })); save.reset() }} className="w-full border border-hairline bg-void px-3 py-2 text-base text-ink disabled:opacity-40" />
                <span className="text-ink-dim">{acceleration ? '1–20 000 pulsos/s²' : '1–4000 pulsos/s'}</span>
              </label>
            })}
          </fieldset>)}
        </div>
        <button type="submit" disabled={!current || !valid || !dirty || save.isPending} className="border border-lock px-4 py-2 text-sm text-lock uppercase disabled:opacity-40">{save.isPending ? 'Guardando…' : 'Guardar ajustes'}</button>
        {!valid && current ? <p className="text-sm text-warn">Introduce enteros dentro de los rangos indicados.</p> : null}
        {save.isSuccess && !dirty ? <p role="status" className="text-sm text-lock">Ajustes guardados. Se aplicarán en el próximo movimiento.</p> : null}
        {settings.isPending ? <p className="text-sm text-ink-dim">Consultando configuración…</p> : null}
        {settings.isError || save.isError ? <p role="alert" className="text-sm text-alert">{save.error?.message ?? settings.error?.message}</p> : null}
        <p className="text-xs text-ink-dim">La aceleración determina cuánto tarda en alcanzar la velocidad. Los valores son consignas; no garantizan que el motor pueda seguirlas sin perder pasos.</p>
      </form>
    </CornerBracketPanel>
  )
}
