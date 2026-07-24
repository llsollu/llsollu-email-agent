// 백엔드 JSON(snake_case)에 맞춘 DTO.

export interface UserInfo {
  id: string
  email: string
  display_name?: string | null
  department?: string | null
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

export interface AgentInfo {
  id: string
  template_key: string
  name: string
  status: string
  error_detail?: string | null
  view_type?: string | null
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
  updated_at?: string | null
  issues: IssueInfo[]
}

export interface RunInfo {
  id: string
  trigger_source: string
  status: string
  error?: string | null
  stats: Record<string, unknown>
}

export type CheckEmailStatus = 'existing' | 'needs_setup' | 'not_company'
