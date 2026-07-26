import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Tailwind 클래스 병합 헬퍼(shadcn 관례). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

/** 내 주소 기준 수신 역할 배지: to=직접수신 / cc=참조 / 그 외=수신. */
export function receiptBadge(role?: string | null): { label: string; cls: string } {
  if (role === 'to') return { label: '직접수신', cls: 'bg-brand2/15 text-brand2' }
  if (role === 'cc') return { label: '참조', cls: 'bg-muted/20 text-muted' }
  return { label: '수신', cls: 'bg-muted/20 text-muted' }
}
