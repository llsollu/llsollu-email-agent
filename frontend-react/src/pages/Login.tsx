import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { api } from '@/lib/api'
import { loadSavedEmail, saveEmail, useAuth } from '@/store/auth'
import { AnimatedBg } from '@/components/AnimatedBg'

export function Login() {
  const setUser = useAuth((s) => s.setUser)
  const [email, setEmail] = useState(loadSavedEmail())
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(true)
  const [saveId, setSaveId] = useState(loadSavedEmail() !== '')
  const [obscure, setObscure] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [setup, setSetup] = useState(false) // 비밀번호 설정 모달

  const canSubmit = email.trim() !== '' && password !== '' && !busy

  async function submit() {
    if (!canSubmit) return
    const em = email.trim().toLowerCase()
    setBusy(true)
    setError(null)
    try {
      const { status } = await api.checkEmail(em)
      if (status === 'not_company') {
        setError('정확한 회사 메일주소를 입력하세요')
        return
      }
      if (status === 'needs_setup') {
        setSetup(true)
        return
      }
      const user = await api.login(em, password, remember)
      saveEmail(saveId ? em : null)
      setUser(user)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function completeSetup(pw: string) {
    const em = email.trim().toLowerCase()
    setBusy(true)
    setError(null)
    try {
      const user = await api.register(em, pw, remember)
      saveEmail(saveId ? em : null)
      setSetup(false)
      setUser(user)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="relative grid min-h-full place-items-center overflow-hidden bg-bg px-6">
      <AnimatedBg />
      <div className="relative w-full max-w-sm rounded-3xl border border-line bg-surface p-8 shadow-[var(--shadow)]">
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-primary to-brand2 text-2xl font-black text-white shadow-lg shadow-primary/30">
          L
        </div>
        <h1 className="text-center text-2xl font-extrabold tracking-tight">LLSOLLU Email Agent</h1>
        <p className="mt-1 text-center text-sm font-medium text-muted">회사 이메일과 비밀번호로 로그인</p>

        <div className="mt-6 space-y-3">
          <input
            className="w-full rounded-xl border border-line bg-surface px-4 py-3 outline-none focus:border-primary"
            placeholder="name@llsollu.com"
            value={email}
            autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
          />
          <div className="relative">
            <input
              className="w-full rounded-xl border border-line bg-surface px-4 py-3 pr-11 outline-none focus:border-primary"
              placeholder="비밀번호"
              type={obscure ? 'password' : 'text'}
              value={password}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
            <button
              type="button"
              aria-label="비밀번호 표시"
              onClick={() => setObscure(!obscure)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted"
            >
              {obscure ? <Eye size={18} /> : <EyeOff size={18} />}
            </button>
          </div>

          <div className="flex flex-col gap-1 pt-1">
            <Check label="이메일 저장" checked={saveId} onChange={setSaveId} />
            <Check label="자동 로그인" checked={remember} onChange={setRemember} />
          </div>

          {error && <p className="text-sm font-semibold text-cancelled">{error}</p>}

          <button
            disabled={!canSubmit}
            onClick={submit}
            className="mt-2 w-full rounded-xl bg-primary py-3 font-bold text-white transition hover:bg-primary-hover disabled:opacity-50"
          >
            {busy ? '처리 중…' : '로그인'}
          </button>
        </div>
      </div>

      {setup && (
        <PasswordSetup
          prefill={password}
          busy={busy}
          onCancel={() => setSetup(false)}
          onConfirm={completeSetup}
        />
      )}
    </div>
  )
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-ink">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4 accent-[var(--primary)]" />
      {label}
    </label>
  )
}

function PasswordSetup({
  prefill, busy, onCancel, onConfirm,
}: { prefill: string; busy: boolean; onCancel: () => void; onConfirm: (pw: string) => void }) {
  const [pw, setPw] = useState(prefill)
  const [pw2, setPw2] = useState('')
  const [err, setErr] = useState<string | null>(null)

  function confirm() {
    if (pw.length < 4) return setErr('비밀번호는 4자 이상이어야 합니다')
    if (pw !== pw2) return setErr('비밀번호가 일치하지 않습니다')
    setErr(null)
    onConfirm(pw)
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 px-6">
      <div className="w-full max-w-sm rounded-2xl border border-line bg-surface p-6 shadow-[var(--shadow)]">
        <h2 className="text-lg font-extrabold">비밀번호 설정</h2>
        <p className="mt-1 text-sm font-medium text-muted">사내 계정이 확인되었습니다. 사용할 비밀번호를 설정하세요.</p>
        <div className="mt-4 space-y-3">
          <input
            className="w-full rounded-xl border border-line bg-surface px-4 py-3 outline-none focus:border-primary"
            placeholder="비밀번호" type="password" value={pw} onChange={(e) => setPw(e.target.value)}
          />
          <input
            className="w-full rounded-xl border border-line bg-surface px-4 py-3 outline-none focus:border-primary"
            placeholder="비밀번호 확인" type="password" value={pw2}
            onChange={(e) => setPw2(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && confirm()}
          />
          {err && <p className="text-sm font-semibold text-cancelled">{err}</p>}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button onClick={onCancel} className="rounded-xl px-4 py-2 font-semibold text-muted hover:bg-line/50">취소</button>
          <button disabled={busy} onClick={confirm} className="rounded-xl bg-primary px-4 py-2 font-bold text-white hover:bg-primary-hover disabled:opacity-50">
            설정하고 로그인
          </button>
        </div>
      </div>
    </div>
  )
}
