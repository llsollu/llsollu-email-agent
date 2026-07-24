import { create } from 'zustand'
import type { UserInfo } from '@/lib/types'

interface AuthState {
  user: UserInfo | null
  setUser: (u: UserInfo | null) => void
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}))

// 이메일 저장(아이디 저장) — localStorage
const EMAIL_KEY = 'saved_email'
export const loadSavedEmail = () => localStorage.getItem(EMAIL_KEY) ?? ''
export const saveEmail = (email: string | null) => {
  if (email) localStorage.setItem(EMAIL_KEY, email)
  else localStorage.removeItem(EMAIL_KEY)
}
