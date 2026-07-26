import type {
  AdminAgent,
  AdminCapacity,
  AdminOps,
  AdminUsage,
  AdminUser,
  AgentInfo,
  CheckEmailStatus,
  ConfigField,
  DashboardData,
  MailRecord,
  ProjectInfo,
  RunInfo,
  TemplateInfo,
  TimelineEntry,
  UserInfo,
} from './types'

// 웹(동일 오리진)은 '', 데스크톱(Tauri)은 사내 서버 절대 URL을 주입.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''
const ROOT = `${API_BASE}/api`

// 데스크톱(Tauri) 대응: 토큰이 있으면 Bearer 로 전송(웹은 httpOnly 쿠키 사용).
let authToken: string | null = null
export function setAuthToken(t: string | null) {
  authToken = t
}

const TOKEN_KEY = 'access_token'
export function isTauri(): boolean {
  return typeof window !== 'undefined' && ('__TAURI_INTERNALS__' in window || '__TAURI__' in window)
}
/** 앱 시작 시(데스크톱) 저장된 토큰 복원. */
export function bootAuth() {
  if (isTauri()) {
    const t = localStorage.getItem(TOKEN_KEY)
    if (t) setAuthToken(t)
  }
}
function captureToken<T extends { access_token?: string | null }>(u: T): T {
  if (isTauri() && u.access_token) {
    setAuthToken(u.access_token)
    localStorage.setItem(TOKEN_KEY, u.access_token)
  }
  return u
}
function clearToken() {
  if (isTauri()) {
    setAuthToken(null)
    localStorage.removeItem(TOKEN_KEY)
  }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) }
  if (opts.body) headers['Content-Type'] = 'application/json'
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  let r: Response
  try {
    r = await fetch(ROOT + path, { credentials: 'include', ...opts, headers })
  } catch {
    throw new ApiError(0, '서버에 연결할 수 없습니다')
  }
  const data = r.status === 204 ? null : await r.json().catch(() => null)
  if (!r.ok) {
    const detail = (data && (data.detail as string)) || `요청 실패 (HTTP ${r.status})`
    throw new ApiError(r.status, detail)
  }
  return data as T
}

const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
const patch = <T>(path: string, body: unknown) =>
  req<T>(path, { method: 'PATCH', body: JSON.stringify(body) })

export const api = {
  // ── dashboard ──
  dashboard: () => req<DashboardData>('/dashboard'),

  // ── admin ──
  adminUsers: () => req<AdminUser[]>('/admin/users'),
  adminPatchUser: (id: string, body: { is_admin?: boolean; is_active?: boolean; reset_password?: boolean }) =>
    patch<{ status: string }>(`/admin/users/${id}`, body),
  adminAgents: () => req<AdminAgent[]>('/admin/agents'),
  adminUsage: () => req<AdminUsage>('/admin/usage'),
  adminOps: () => req<AdminOps>('/admin/ops'),
  adminCapacity: () => req<AdminCapacity>('/admin/capacity'),
  adminPruneRuns: () => post<{ deleted: number }>('/admin/maintenance/prune-runs'),
  adminArchiveProjects: () => post<{ archived: number }>('/admin/maintenance/archive-projects'),

  // ── auth ──
  me: () => req<UserInfo>('/me'),
  checkEmail: (email: string) =>
    post<{ status: CheckEmailStatus; display_name?: string | null }>('/auth/check-email', { email }),
  login: (email: string, password: string, remember: boolean) =>
    post<UserInfo>('/auth/login', { email, password, remember }).then(captureToken),
  register: (email: string, password: string, remember: boolean) =>
    post<UserInfo>('/auth/register', { email, password, remember }).then(captureToken),
  logout: () => post<{ status: string }>('/auth/logout').finally(clearToken),

  // ── templates ──
  templates: () => req<TemplateInfo[]>('/templates'),
  configSchema: (key: string) => req<ConfigField[]>(`/templates/${key}/config-schema`),
  mailSchedulerColumns: (fileUrl: string) =>
    post<{ columns: string[]; sample: Record<string, string>; row_count: number }>(
      '/templates/mail_scheduler/columns',
      { file_url: fileUrl },
    ),

  // ── agents ──
  agents: () => req<AgentInfo[]>('/agents'),
  agent: (id: string) => req<AgentInfo>(`/agents/${id}`),
  createAgent: (template_key: string, name: string, config: Record<string, unknown>, secrets: Record<string, unknown> = {}) =>
    post<AgentInfo>('/agents', { template_key, name, config, secrets }),
  updateAgent: (id: string, body: { name?: string; config?: Record<string, unknown>; secrets?: Record<string, unknown> }) =>
    patch<AgentInfo>(`/agents/${id}`, body),
  deleteAgent: (id: string) => req<null>(`/agents/${id}`, { method: 'DELETE' }),
  runNow: (id: string, dryRun = false) =>
    post<{ status: string }>(`/agents/${id}/run?dry_run=${dryRun}`),

  // ── project_tracker ──
  projects: (agentId: string, includeArchived = false) =>
    req<ProjectInfo[]>(`/agents/${agentId}/projects${includeArchived ? '?include_archived=true' : ''}`),
  setProjectStatus: (agentId: string, projectId: string, status: string) =>
    patch(`/agents/${agentId}/projects/${projectId}/status`, { status }),

  // ── mail_timeline ──
  timeline: (agentId: string, opts: { before?: string; limit?: number } = {}) => {
    const q = new URLSearchParams()
    if (opts.before) q.set('before', opts.before)
    if (opts.limit) q.set('limit', String(opts.limit))
    const qs = q.toString()
    return req<TimelineEntry[]>(`/agents/${agentId}/timeline${qs ? `?${qs}` : ''}`)
  },
  message: (agentId: string, messageId: string) =>
    req<MailRecord>(`/agents/${agentId}/messages/${messageId}`),

  // ── mail_scheduler ──
  runs: (agentId: string) => req<RunInfo[]>(`/agents/${agentId}/runs`),
  schedule: (agentId: string) => req<Record<string, unknown> | null>(`/agents/${agentId}/schedule`),
  toggleSchedule: (agentId: string, enabled: boolean) =>
    patch(`/agents/${agentId}/schedule`, { enabled }),
}
