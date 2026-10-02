import { NavLink } from 'react-router-dom'
import { ConnectionStatusIndicator } from '../status/ConnectionStatusIndicator'
import { StatusBadge } from '../hud/StatusBadge'

interface TopBarProps {
  serialConnected: boolean
  socketConnected: boolean
}

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 pb-3 -mb-px font-cond text-xs tracking-[0.1em] uppercase ${
    isActive ? 'border-accent text-ink' : 'border-transparent text-ink-dim hover:text-ink'
  }`

export function TopBar({ serialConnected, socketConnected }: TopBarProps) {
  return (
    <header className="shrink-0 border-b border-hairline bg-panel px-6">
      <div className="flex items-center justify-between pt-4">
        <div className="flex items-center gap-4">
          <span className="font-cond text-lg tracking-[0.1em] text-ink">AI-RMY</span>
          <span className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] tracking-[0.1em] text-ink-dim normal-case">
            REV.02
          </span>
          <nav className="ml-4 flex flex-wrap gap-x-6 gap-y-3">
            <NavLink to="/live" className={NAV_LINK_CLASS}>
              Live view
            </NavLink>
            <NavLink to="/people" className={NAV_LINK_CLASS}>
              Known faces
            </NavLink>
            <NavLink to="/manual" className={NAV_LINK_CLASS}>
              Manual mode
            </NavLink>
            <NavLink to="/scan" className={NAV_LINK_CLASS}>
              Room scan
            </NavLink>
            <NavLink to="/settings" className={NAV_LINK_CLASS}>Configuración</NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-5 pb-3">
          <ConnectionStatusIndicator connected={serialConnected} label="Gimbal" />
          <StatusBadge status={socketConnected ? 'lock' : 'alert'} label={`Events ${socketConnected ? 'live' : 'down'}`} />
        </div>
      </div>
    </header>
  )
}
