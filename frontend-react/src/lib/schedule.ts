// '확인 주기' 친화적 UI ↔ cron 변환/표시 (Dart schedule_util.dart 이식).
// scheduleUi: { kind: daily|weekly|monthly|hourly|minutely, hour, minute, weekday(1=월..7=일), day, interval }

export const WEEKDAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']

export type ScheduleUi = {
  kind?: string
  hour?: number
  minute?: number
  weekday?: number
  day?: number
  interval?: number
}

const two = (n: number) => String(n).padStart(2, '0')

export function cronFromScheduleUi(s: ScheduleUi): string {
  const minute = s.minute ?? 0
  const hour = s.hour ?? 9
  switch (s.kind) {
    case 'weekly': {
      const wd = s.weekday ?? 1
      return `${minute} ${hour} * * ${wd === 7 ? 0 : wd}`
    }
    case 'monthly':
      return `${minute} ${hour} ${s.day ?? 1} * *`
    case 'hourly':
      return `${minute} * * * *`
    case 'minutely':
      return `*/${s.interval ?? 30} * * * *`
    default:
      return `${minute} ${hour} * * *`
  }
}

export function humanFromScheduleUi(s: ScheduleUi): string {
  const hm = `${two(s.hour ?? 9)}:${two(s.minute ?? 0)}`
  switch (s.kind) {
    case 'weekly':
      return `매주 ${WEEKDAY_NAMES[((s.weekday ?? 1) - 1 + 7) % 7]}요일 ${hm}`
    case 'monthly':
      return `매월 ${s.day ?? 1}일 ${hm}`
    case 'hourly':
      return `매시 ${s.minute ?? 0}분`
    case 'minutely':
      return `${s.interval ?? 30}분마다`
    default:
      return `매일 ${hm}`
  }
}

export function scheduleUiFromCron(cron?: string | null): ScheduleUi | null {
  if (!cron) return null
  const p = cron.trim().split(/\s+/)
  if (p.length !== 5) return null
  const [mn, hr, dom, , dow] = p
  const pi = (v: string) => (/^\d+$/.test(v) ? parseInt(v, 10) : null)

  if (mn.startsWith('*/') && hr === '*' && dom === '*' && dow === '*')
    return { kind: 'minutely', interval: parseInt(mn.slice(2), 10) || 30 }
  if (pi(mn) !== null && hr === '*' && dom === '*' && dow === '*')
    return { kind: 'hourly', minute: pi(mn)! }
  if (pi(mn) !== null && pi(hr) !== null && dom === '*' && dow !== '*') {
    const c = pi(dow)!
    return { kind: 'weekly', minute: pi(mn)!, hour: pi(hr)!, weekday: c === 0 ? 7 : c }
  }
  if (pi(mn) !== null && pi(hr) !== null && dom !== '*')
    return { kind: 'monthly', minute: pi(mn)!, hour: pi(hr)!, day: pi(dom)! }
  if (pi(mn) !== null && pi(hr) !== null)
    return { kind: 'daily', minute: pi(mn)!, hour: pi(hr)! }
  return null
}

export function humanFromCron(cron?: string | null): string {
  const ui = scheduleUiFromCron(cron)
  return ui ? humanFromScheduleUi(ui) : cron ?? '-'
}
