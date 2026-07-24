import type {
  AgentInfo,
  CheckEmailStatus,
  ConfigField,
  ProjectInfo,
  RunInfo,
  TemplateInfo,
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

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) }
  if (opts.body) headers['Content-Type'] = 'application/json'
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  const r = await fetch(ROOT + path, { credentials: 'include', ...opts, headers })
  const data = r.status === 204 ? null : await r.json().catch(() => null)
  if (!r.ok) {
    const detail = (data && (data.detail as string)) || `요청 실패 (HTTP ${r.status})`
    throw new Error(detail)
  }
  return data as T
}

const post = <T>(path: string, body?: unknown) =>
  req<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
const patch = <T>(path: string, body: unknown) =>
  req<T>(path, { method: 'PATCH', body: JSON.stringify(body) })

export const api = {
  // ── auth ──
  me: () => req<UserInfo>('/me'),
  checkEmail: (email: string) =>
    post<{ status: CheckEmailStatus; display_name?: string | null }>('/auth/check-email', { email }),
  login: (email: string, password: string, remember: boolean) =>
    post<UserInfo>('/auth/login', { email, password, remember }),
  register: (email: string, password: string, remember: boolean) =>
    post<UserInfo>('/auth/register', { email, password, remember }),
  logout: () => post<{ status: string }>('/auth/logout'),

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
  projects: (agentId: string) => req<ProjectInfo[]>(`/agents/${agentId}/projects`),
  setProjectStatus: (agentId: string, projectId: string, status: string) =>
    patch(`/agents/${agentId}/projects/${projectId}/status`, { status }),

  // ── mail_scheduler ──
  runs: (agentId: string) => req<RunInfo[]>(`/agents/${agentId}/runs`),
  schedule: (agentId: string) => req<Record<string, unknown> | null>(`/agents/${agentId}/schedule`),
  toggleSchedule: (agentId: string, enabled: boolean) =>
    patch(`/agents/${agentId}/schedule`, { enabled }),
}
