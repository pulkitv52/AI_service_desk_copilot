import {
  ChatResponse,
  DeviceHealthResponse,
  RemediationResultResponse,
  TicketResponse
} from '@/types'

const BASE_URL = ''

export class ManualReconciliationError extends Error {
  constructor() {
    super('Multiple incidents match this conversation. Manual reconciliation in ServiceNow is required; another creation attempt remains blocked.')
    this.name = 'ManualReconciliationError'
  }
}

async function throwWorkflowError(response: Response): Promise<never> {
  const body = await response.json().catch(() => null)
  if (response.status === 409 && body?.detail?.code === 'manual_reconciliation_required') {
    throw new ManualReconciliationError()
  }
  throw new Error(`Support workflow unavailable (${response.status})`)
}

export async function sendChatMessage(
  message: string,
  sessionId?: string,
  forceTicket: boolean = false
): Promise<ChatResponse> {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      force_ticket: forceTicket
    })
  })

  if (!response.ok) {
    await throwWorkflowError(response)
  }

  return response.json()
}

export async function fetchDeviceHealth(
  deviceId: string = 'EMP-LT-104'
): Promise<DeviceHealthResponse> {
  const response = await fetch(`${BASE_URL}/api/devices/${deviceId}/health`)
  if (!response.ok) {
    throw new Error(`Device health fetch failed: ${response.statusText}`)
  }
  return response.json()
}

export async function triggerDeviceRemediation(
  deviceId: string,
  toolName: string,
  dryRun: boolean = false
): Promise<RemediationResultResponse> {
  const response = await fetch(`${BASE_URL}/api/devices/${deviceId}/remediate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      tool_name: toolName,
      dry_run: dryRun,
      reason: 'Self-healing triggered from Service Desk Copilot'
    })
  })

  if (!response.ok) {
    throw new Error(`Remediation failed: ${response.statusText}`)
  }

  return response.json()
}

export async function fetchRecentTickets(): Promise<TicketResponse[]> {
  const response = await fetch(`${BASE_URL}/api/tickets?limit=10`)
  if (!response.ok) {
    return []
  }
  return response.json()
}

export async function checkSystemHealth(): Promise<{
  status: string
  servicenow_configured: boolean
  version: string
}> {
  const response = await fetch(`${BASE_URL}/health`)
  if (!response.ok) {
    throw new Error('System health check failed')
  }
  return response.json()
}

export async function fetchConversations(): Promise<import('@/types').ConversationSummary[]> {
  const response = await fetch('/api/conversations')
  if (!response.ok) throw new Error('Conversation history unavailable')
  return response.json()
}

export async function fetchConversation(id: string): Promise<import('@/types').ConversationDetail> {
  const response = await fetch(`/api/conversations/${id}`)
  if (!response.ok) throw new Error('Unable to open conversation')
  return response.json()
}

export async function reconcileIncident(id: string): Promise<{ status: string; ticket?: TicketResponse }> {
  const response = await fetch(`/api/conversations/${id}/reconcile`, { method: 'POST' })
  if (!response.ok) await throwWorkflowError(response)
  return response.json()
}

export async function startConversation(): Promise<import('@/types').ConversationSummary> {
  const response = await fetch('/api/conversations', { method: 'POST' })
  if (!response.ok) throw new Error('Unable to start conversation')
  return response.json()
}
