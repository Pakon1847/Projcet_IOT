import { useEffect, useRef, useState } from 'react'

/**
 * Smoothly counts from 0 → target whenever `target` changes.
 * Returns the current display value (rounded to `decimals` places).
 */
export function useCountUp(target: number, duration = 700, decimals = 0) {
  const [display, setDisplay] = useState(target)
  const rafRef  = useRef<number>(0)
  const prevRef = useRef(target)

  useEffect(() => {
    const from  = prevRef.current
    const start = performance.now()

    const tick = (now: number) => {
      const elapsed  = now - start
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased    = 1 - Math.pow(1 - progress, 3)
      const current  = from + (target - from) * eased
      setDisplay(parseFloat(current.toFixed(decimals)))
      if (progress < 1) rafRef.current = requestAnimationFrame(tick)
      else              prevRef.current = target
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration, decimals])

  return display
}
