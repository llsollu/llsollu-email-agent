import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

type Mode = 'light' | 'dark'
const KEY = 'theme_mode'

function systemMode(): Mode {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}
function apply(mode: Mode) {
  document.documentElement.setAttribute('data-theme', mode)
}

/** 라이트/다크 토글. 선택값을 localStorage에 저장. */
export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>(() => (localStorage.getItem(KEY) as Mode) || systemMode())

  useEffect(() => {
    apply(mode)
    localStorage.setItem(KEY, mode)
  }, [mode])

  return (
    <button
      onClick={() => setMode(mode === 'dark' ? 'light' : 'dark')}
      aria-label="테마 전환"
      className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-muted hover:bg-line/50"
    >
      {mode === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      {mode === 'dark' ? '라이트 모드' : '다크 모드'}
    </button>
  )
}
