import type { ReactNode } from 'react'

type BracketColor = 'hairline' | 'lock' | 'warn' | 'alert'

const COLOR_CLASS: Record<BracketColor, string> = {
  hairline: 'border-hairline',
  lock: 'border-lock',
  warn: 'border-warn',
  alert: 'border-alert',
}

interface CornerBracketPanelProps {
  title?: string
  color?: BracketColor
  pulse?: boolean
  padded?: boolean
  /** Tighter padding/title spacing, for layouts that stack several panels
   * where vertical footprint matters more than breathing room (e.g. the
   * LiveViewPage sidebar). Doesn't change any other caller. */
  compact?: boolean
  className?: string
  children: ReactNode
}

// The one reused structural device across the app: an open-corner frame
// instead of a rounded card + shadow. Corners are drawn independently of
// the panel's own (hairline) border so a locked/alert state can highlight
// just the brackets without restyling the whole panel.
export function CornerBracketPanel({
  title,
  color = 'hairline',
  pulse = false,
  padded = true,
  compact = false,
  className = '',
  children,
}: CornerBracketPanelProps) {
  const bracketClass = `absolute h-3.5 w-3.5 ${COLOR_CLASS[color]} ${
    pulse ? 'animate-lock-pulse' : ''
  }`
  const paddingClass = padded ? (compact ? 'p-2' : 'p-4') : ''

  return (
    <div className={`relative border border-hairline bg-panel ${paddingClass} ${className}`}>
      <span className={`${bracketClass} top-0 left-0 border-t-2 border-l-2`} />
      <span className={`${bracketClass} top-0 right-0 border-t-2 border-r-2`} />
      <span className={`${bracketClass} bottom-0 left-0 border-b-2 border-l-2`} />
      <span className={`${bracketClass} bottom-0 right-0 border-b-2 border-r-2`} />

      {title ? (
        <p className={`field-label ${padded ? (compact ? 'mb-1.5' : 'mb-3') : 'p-4 pb-0 mb-0'}`}>{title}</p>
      ) : null}
      {children}
    </div>
  )
}
