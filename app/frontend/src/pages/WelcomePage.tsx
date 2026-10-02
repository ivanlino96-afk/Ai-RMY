import { useNavigate } from 'react-router-dom'
import { GimbalIdleAnimation } from '../components/hud/GimbalIdleAnimation'
import { StatusBadge } from '../components/hud/StatusBadge'

const CAPABILITIES = ['Seguimiento', 'Reconocimiento', 'Defensa', 'Escaneo']

// Entry point of the app, outside AppShell on purpose: no operational
// TopBar/nav here, this is shown before the system is "started". The CTA
// below is the only way in — it hands off to the real dashboard at /live.
export function WelcomePage() {
  const navigate = useNavigate()

  return (
    <div className="flex h-screen flex-col overflow-y-auto bg-void">
      <header className="flex shrink-0 items-center justify-between border-b border-hairline px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="font-cond text-lg tracking-[0.1em] text-ink">AI-RMY</span>
          <span className="border border-hairline px-1.5 py-0.5 font-mono text-[9px] tracking-[0.1em] text-ink-dim normal-case">
            SYS-00
          </span>
        </div>
        <StatusBadge status="idle" label="Standby" />
      </header>

      <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col items-center justify-center px-6 py-10">
        <div className="grid w-full grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <p className="field-label text-accent">Sistema de seguridad</p>
            <h1 className="mt-2 text-[clamp(48px,9vw,104px)] leading-[0.95] tracking-[-0.02em] text-ink uppercase">
              AI-RMY
            </h1>
            <p className="mt-6 max-w-md text-sm leading-relaxed text-ink-dim">
              Gimbal de seguimiento facial en tiempo real: detecta rostros,
              reconoce personas conocidas y centra la cámara sobre el
              objetivo. Ante un rostro no identificado, activa el modo
              defensa/alarma automáticamente.
            </p>

            <div className="mt-6 flex flex-wrap gap-2">
              {CAPABILITIES.map((label) => (
                <span key={label} className="border border-hairline px-2 py-1 font-mono text-[10px] tracking-[0.1em] text-ink-dim uppercase">
                  {label}
                </span>
              ))}
            </div>

            <button
              onClick={() => navigate('/live')}
              className="mt-10 border border-accent px-6 py-3 text-sm text-accent transition-colors hover:bg-accent hover:text-void"
            >
              Iniciar sistema →
            </button>
          </div>

          <GimbalIdleAnimation />
        </div>
      </main>
    </div>
  )
}
