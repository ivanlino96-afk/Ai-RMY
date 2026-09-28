import { useEffect, useState } from 'react'

// Pure UI timing: true once `value` has stayed true continuously for
// `holdMs`. While value stays true across renders (same primitive), the
// effect doesn't restart, so the timer counts from the first true — not
// from every frame. Any false in between cancels the pending timer and
// resets immediately, restarting the hold window.
export function useHeldTrue(value: boolean, holdMs: number): boolean {
  const [held, setHeld] = useState(false)

  useEffect(() => {
    if (!value) {
      setHeld(false)
      return
    }
    const timer = setTimeout(() => setHeld(true), holdMs)
    return () => clearTimeout(timer)
  }, [value, holdMs])

  return held
}
