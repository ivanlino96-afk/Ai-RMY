import { useSetTrackingMode } from '../../api/gimbal'
import type { GimbalStatus } from '../../types/api'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'
import { StatusBadge } from '../hud/StatusBadge'

export function TrackingModePanel({ status }: { status: GimbalStatus | undefined }) {
  const tracking = useSetTrackingMode()
  const enabled = status?.tracking_enabled

  return (
    <CornerBracketPanel title="Seguimiento automático" color={enabled ? 'warn' : 'hairline'} compact>
      <div className="space-y-2">
        <StatusBadge status={enabled ? 'warn' : 'idle'} label={enabled === undefined ? 'Consultando estado' : enabled ? 'Activado' : 'Desactivado'} />
        <button
          type="button"
          aria-pressed={enabled ?? false}
          disabled={enabled === undefined || tracking.isPending}
          onClick={() => tracking.mutate(!enabled)}
          className="w-full border border-lock px-3 py-3 text-xs tracking-[0.1em] text-lock uppercase hover:bg-lock hover:text-void disabled:opacity-40"
        >
          {tracking.isPending ? 'Aplicando…' : enabled ? 'Desactivar seguimiento' : 'Activar seguimiento'}
        </button>
        <p className="text-xs text-ink-dim">
          {enabled ? 'La cámara puede ordenar movimientos de los motores.' : 'Seguimiento pausado. Usa Manual Mode para las pruebas.'}
        </p>
        {tracking.isError ? <p role="alert" className="text-xs text-alert">{tracking.error.message}</p> : null}
      </div>
    </CornerBracketPanel>
  )
}
