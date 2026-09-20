import { StatusBadge } from '../hud/StatusBadge'

interface ConnectionStatusIndicatorProps {
  connected: boolean
  label: string
}

export function ConnectionStatusIndicator({ connected, label }: ConnectionStatusIndicatorProps) {
  return (
    <StatusBadge status={connected ? 'lock' : 'alert'} label={`${label} ${connected ? 'online' : 'offline'}`} />
  )
}
