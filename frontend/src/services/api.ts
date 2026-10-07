import {
  ChatResponse,
  DeviceHealthResponse,
  RemediationResultResponse,
  TicketResponse
} from '@/types'

const BASE_URL = ''

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
    const errorText = await response.text()
    throw new Error(`Chat API error (${response.status}): ${errorText}`)
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
