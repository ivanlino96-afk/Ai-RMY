import { useState } from 'react'
import { CornerBracketPanel } from '../hud/CornerBracketPanel'

interface Props {
  axis: 'pan' | 'tilt'
  value: number | null
  calibration: boolean
  disabled: boolean
  moving: boolean
  speed?: number
  onMove: (amount: number) => void
}

function AxisDiagram({ axis }: { axis: 'pan' | 'tilt' }) {
  const pan = axis === 'pan'
  return (
    <svg viewBox="0 0 220 190" className="max-h-[180px] w-full text-ink-dim" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeWidth="1">
        <path d="M10 95H210M110 8V182" opacity=".2" />
        <circle cx="110" cy="95" r="76" strokeDasharray="2 7" opacity=".4" />
        <circle cx="110" cy="95" r="61" opacity=".35" />
        {Array.from({ length: 24 }, (_, i) => <path key={i} d={i % 3 === 0 ? 'M110 21v9' : 'M110 21v4'} transform={`rotate(${i * 15} 110 95)`} opacity={i % 3 === 0 ? '.7' : '.35'} />)}
        {pan ? <>
          <ellipse cx="110" cy="115" rx="43" ry="20" />
          <path d="M67 115v10c0 26 86 26 86 0v-10M89 111V70h42v41M89 70l10-12h42l-10 12M131 70l10-12v44l-10 9" />
          <circle cx="110" cy="88" r="10" />
          <path d="M52 80a60 60 0 0 1 96-30m-9-1 9 1-2-9" strokeWidth="2" />
        </> : <>
          <path d="M66 133h88M74 133v-13h72v13M83 120V70m54 50V70" />
          <path d="M83 94l44-32 20 28-44 32zM92 88l20 28" />
          <circle cx="110" cy="95" r="5" />
          <path d="M165 55a69 69 0 0 1 0 80m0-10v10l10-2" strokeWidth="2" />
        </>}
        <path d="M10 28V12h18M192 12h18v16M10 162v16h18M192 178h18v-16" opacity=".5" />
      </g>
      <text x="110" y="187" textAnchor="middle" fill="currentColor" fontSize="7" letterSpacing="2">{pan ? 'VISTA SUPERIOR' : 'VISTA LATERAL'}</text>
    </svg>
  )
}

export function AxisInstrument({ axis, value, calibration, disabled, moving, speed, onMove }: Props) {
  const [amount, setAmount] = useState('20')
  const [degrees, setDegrees] = useState('1')
  const selected = calibration ? amount : degrees
  const setSelected = calibration ? setAmount : setDegrees
  const parsed = Number(selected)
  const maximum = calibration ? 2000 : axis === 'pan' ? 45 : 30
  const valid = selected.trim() !== '' && Number.isFinite(parsed) && parsed > 0 && parsed <= maximum && (!calibration || Number.isInteger(parsed))
  const unit = calibration ? 'pulsos' : '°'
  const formatted = value === null ? '—' : `${value > 0 ? '+' : ''}${new Intl.NumberFormat('es-MX', { maximumFractionDigits: calibration ? 0 : 2 }).format(value)}`
  return (
    <CornerBracketPanel padded={false}>
      <header className="flex items-center justify-between gap-2 border-b border-hairline px-5 py-4">
        <div>
          <span className="field-label">EJE {axis === 'pan' ? '01 / HORIZONTAL' : '02 / VERTICAL'}</span>
          <h2 className="mt-1 text-xl normal-case tracking-[0.06em] text-ink">
            {axis.toUpperCase()} <span className="ml-2 text-xs text-ink-dim normal-case">{axis === 'pan' ? 'Azimut' : 'Elevación'}</span>
          </h2>
        </div>
        <span className={`inline-flex items-center gap-2 whitespace-nowrap font-mono text-[9px] normal-case tracking-[0.08em] ${moving ? 'text-warn' : 'text-ink-dim'}`}>
          <i className={`h-1.5 w-1.5 ${moving ? 'bg-warn' : 'bg-ink-dim'}`} />
          {value === null ? 'SIN DATOS' : moving ? 'EN MOVIMIENTO*' : 'EN ESPERA'}
        </span>
      </header>
      <div className="grid grid-cols-[1.25fr_1fr] items-center gap-2 px-5 py-6">
        <div className="min-w-0">
          <span className="field-label">{calibration ? 'CONTADOR DESDE CERO' : 'POSICIÓN ESTIMADA'}</span>
          <output aria-label={`${axis} ${calibration ? 'pulsos emitidos' : 'grados estimados'}`} className="text-readout mt-1 block text-ink">{formatted}</output>
          <span className="field-label">{calibration ? 'PULSOS STEP EMITIDOS' : 'GRADOS RELATIVOS AL ORIGEN'}</span>
          <div className="mt-4 flex items-center gap-3 border-t border-hairline pt-3 font-mono text-[9px] normal-case text-ink-dim">
            <span>VELOCIDAD MÁX.</span>
            <strong className="text-base font-normal normal-case text-ink">{speed ?? '—'} <small className="text-[9px] text-ink-dim">pulsos/s</small></strong>
          </div>
        </div>
        <AxisDiagram axis={axis} />
      </div>
      <div className="border-t border-hairline bg-void/40 px-5 py-5">
        <div className="flex items-center justify-between gap-3 border border-hairline bg-panel px-3">
          <label htmlFor={`increment-${axis}`} className="text-xs normal-case text-ink-dim">Incremento por orden</label>
          <div className="flex items-center">
            <input id={`increment-${axis}`} aria-label={`Incremento ${axis}`} type="number" min={calibration ? 1 : 0.1} max={maximum} step={calibration ? 1 : 0.1} value={selected} disabled={disabled} onChange={e => setSelected(e.target.value)} className="w-24 bg-transparent py-2 text-base text-ink" />
            <span className="field-label pr-1">{unit}</span>
          </div>
        </div>
        <div className="mt-3 flex gap-2" aria-label={`Incrementos rápidos ${axis}`}>
          {(calibration ? [20, 100, 500, 2000] : [1, 5, 10]).map(n => (
            <button
              key={n}
              disabled={disabled}
              className={`flex-1 border px-1 py-2 text-[10px] ${parsed === n ? 'border-accent bg-accent/10 text-ink' : 'border-hairline text-ink-dim hover:border-ink-dim'}`}
              onClick={() => setSelected(String(n))}
            >
              {n} {unit}
            </button>
          ))}
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <button disabled={disabled || !valid} onClick={() => onMove(-parsed)} aria-label={`Mover ${axis} negativo`} className="border border-hairline bg-panel px-2 py-3 text-xs text-ink hover:border-ink-dim disabled:opacity-40">
            <span className="mr-3 text-lg align-middle">−</span> Mover {axis.toUpperCase()}
          </button>
          <button disabled={disabled || !valid} onClick={() => onMove(parsed)} aria-label={`Mover ${axis} positivo`} className="border border-hairline bg-panel px-2 py-3 text-xs text-ink hover:border-ink-dim disabled:opacity-40">
            <span className="mr-3 text-lg align-middle">+</span> Mover {axis.toUpperCase()}
          </button>
        </div>
        {!valid ? <p className="mt-2 text-[10px] normal-case text-warn">Usa {calibration ? 'un entero' : 'un valor'} entre {calibration ? 1 : 0.1} y {maximum}.</p> : null}
      </div>
    </CornerBracketPanel>
  )
}
