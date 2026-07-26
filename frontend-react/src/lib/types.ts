// 백엔드 JSON(snake_case)에 맞춘 DTO.

export interface UserInfo {
  id: string
  email: string
  display_name?: string | null
  department?: string | null
  access_token?: string | null
}

export interface TemplateInfo {
  key: string
  name: string
  version: string
  description: string
  trigger_kind: string
  view_type: string
}

export interface ConfigField {
  key: string
  label: string
  type: string
  required: boolean
  secret: boolean
  help?: string | null
  options?: string[] | null
  default?: unknown
}

export interface AgentView {
  key: string
  type: string
  label: string
}

export interface AgentInfo {
  id: string
  template_key: string
  name: string
  status: string
  error_detail?: string | null
  view_type?: string | null
  views?: AgentView[]
  config: Record<string, unknown>
}

export interface IssueInfo {
  id: string
  type: string
  summary: string
  severity: string
  status: string
}

export interface ProjectInfo {
  id: string
  client_name: string
  title: string
  status: string
  category?: string | null
  priority?: string | null
  latest_update?: string | null
  keywords?: string[] | null
  from_name?: string | null
  from_address?: string | null
  recipient_role?: string | null
  updated_at?: string | null
  archived_at?: string | null
  source_message_id?: string | null
  issues: IssueInfo[]
}

export interface TimelineEntry {
  id: string
  client_name?: string | null
  project_title?: string | null
  category?: string | null
  subject?: string | null
  from_address?: string | null
  from_name?: string | null
  direction: string
  received_at?: string | null
  summary?: string | null
  action_required?: boolean
  issue?: { type?: string; summary?: string; severity?: string } | null
  points?: string[] | null
  keywords?: string[] | null
  recipient_role?: string | null
}

export interface MailRecord extends TimelineEntry {
  mailbox: string
  body_text?: string | null
  to_recipients?: string | null
  cc_recipients?: string | null
}

export interface RunInfo {
  id: string
  trigger_source: string
  status: string
  error?: string | null
  stats: Record<string, unknown>
}

export type CheckEmailStatus = 'existing' | 'needs_setup' | 'not_company'

export interface AnalysisStats {
  kpis: {
    week_analyzed: number; week_prev: number
    open_issues: number; severity: Record<string, number>
    active_cards: number; statuses: Record<string, number>
    direct_ratio: number
  }
  daily: { date: string; count: number }[]
  categories: { name: string; count: number }[]
  clients: { name: string; count: number }[]
  issue_types: { type: string; count: number }[]
  receipt: { to: number; cc: number; other: number }
  llm: { tokens_in: number; tokens_out: number; count: number }
}

export interface SchedulerStats {
  kpis: {
    week_sent: number; week_failed: number
    active_schedules: number; total_schedulers: number
    next_run_at: string | null
  }
  daily: { date: string; sent: number; failed: number }[]
  agents: { id: string; name: string; next_run_at: string | null; enabled: boolean; week_sent: number; week_failed: number }[]
  recent: { agent: string; subject: string; status: string; sent_at: string | null }[]
}

export interface DashboardData {
  agents: { id: string; name: string; template_key: string; status: string; view_type?: string | null }[]
  analysis: AnalysisStats | null
  scheduler: SchedulerStats | null
}
