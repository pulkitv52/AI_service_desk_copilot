export type SupportIntent =
  | 'knowledge_inquiry'
  | 'software_request'
  | 'application_issue'
  | 'diagnostic_remediation'
  | 'general_incident'

export type TicketPriority = 'P1' | 'P2' | 'P3' | 'P4' | 'P5'

export interface IntentClassification {
  intent: SupportIntent
  category: string
  subcategory?: string
  application?: string
  urgency: string
  impact: string
  priority: TicketPriority
  assignment_group: string
  confidence: number
  reasoning?: string
}

export interface TicketResponse {
  sys_id: string
  number: string
  short_description: string
  description?: string
  state: string
  urgency: string
  impact: string
  priority?: string
  category?: string
  subcategory?: string
  assignment_group?: string
  caller_id?: string
  provider: string
  created_at: string
  updated_at?: string
}

export type ChatResponseType =
  | 'deflected_rag'
  | 'ticket_created'
  | 'service_request'
  | 'diagnostic_action'
  | 'escalation_offered'
  | 'conversational'
  | 'pending_verification'
  | 'ticket_failed'

export interface ChatResponse {
  session_id: string
  response_type: ChatResponseType
  message: string
  classification: IntentClassification
  ticket?: TicketResponse
  sources: string[]
  created_at: string
}

export interface ChatMessage {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp: string
  responseType?: ChatResponseType
  classification?: IntentClassification
  ticket?: TicketResponse
  sources?: string[]
}

export interface DeviceHealthResponse {
  device_id: string
  hostname: string
  os: string
  cpu_usage: number
  memory_usage: number
  disk_free_gb: number
  disk_total_gb: number
  teams_crashes_24h: number
  network_latency_ms: number
  vpn_connected: boolean
  health_status: 'healthy' | 'warning' | 'critical'
  last_seen: string
}

export interface RemediationResultResponse {
  action_id: string
  device_id: string
  tool_name: string
  status: string
  dry_run: boolean
  before_state: Record<string, unknown>
  after_state: Record<string, unknown>
  output: string
  resolved: boolean
  executed_at: string
}

export interface ConversationSummary {
  id: string
  issue: string
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  incident_status?: string
  ticket?: TicketResponse
  messages: {
    id: number
    role: 'user' | 'assistant'
    content: string
    created_at: string
    response?: ChatResponse
  }[]
}
