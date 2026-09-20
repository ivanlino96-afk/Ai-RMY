import { NavLink } from 'react-router-dom'
import { ConnectionStatusIndicator } from '../status/ConnectionStatusIndicator'
import { StatusBadge } from '../hud/StatusBadge'

interface TopBarProps {
  serialConnected: boolean
  socketConnected: boolean
}

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 pb-3 -mb-px text-xs tracking-[0.1em] uppercase ${
    isActive ? 'border-lock text-ink' : 'border-transparent text-ink-dim hover:text-ink'
  }`

export function TopBar({ serialConnected, socketConnected }: TopBarProps) {
  return (
    <header className="border-b border-hairline bg-panel px-6">
      <div className="flex items-center justify-between pt-4">
        <div className="flex items-center gap-8">
          <span className="text-sm tracking-[0.14em] text-ink">AI-RMY</span>
          <nav className="flex gap-6">
            <NavLink to="/" end className={NAV_LINK_CLASS}>
              Live view
            </NavLink>
            <NavLink to="/people" className={NAV_LINK_CLASS}>
              Known faces
            </NavLink>
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
