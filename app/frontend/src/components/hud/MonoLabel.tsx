import type { ReactNode } from 'react'

interface MonoLabelProps {
  children: ReactNode
  className?: string
}

// The instrument-panel field label: PAN, TILT, STATUS, TARGET. Scoped to
// actual field labels on data, not decorative eyebrows over prose.
export function MonoLabel({ children, className = '' }: MonoLabelProps) {
  return <span className={`field-label ${className}`}>{children}</span>
}
