import { useEffect } from 'react'

/** Esc 키로 모달 등을 닫는다. */
export function useEscape(onEscape: () => void) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onEscape()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onEscape])
}
