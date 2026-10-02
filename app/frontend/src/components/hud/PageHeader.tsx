import type { ReactNode } from 'react'

interface PageHeaderProps {
  code: string
  title: string
  subtitle?: string
  action?: ReactNode
}

// Spec-sheet style page banner: system code + title, optional subtitle and
// a trailing action slot (e.g. an emergency-stop button). Not sticky/bleeding
// on purpose -- pages vary in container width (full-bleed grids vs. a
// centered max-w column on SettingsPage), so this stays a plain in-flow
// block that respects whatever width its caller gives it.
export function PageHeader({ code, title, subtitle, action }: PageHeaderProps) {
  return (
    <header className="mb-6 flex items-center justify-between gap-4 border-b border-hairline pb-4">
      <div>
        <p className="field-label text-accent">{code}</p>
        <h1 className="mt-1 text-2xl text-ink">
          {title}
          {subtitle ? <span className="ml-3 border border-hairline px-1.5 py-0.5 align-middle font-mono text-[10px] tracking-[0.1em] text-ink-dim normal-case">{subtitle}</span> : null}
        </h1>
      </div>
      {action}
    </header>
  )
}
