import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, Sparkles, RefreshCw } from 'lucide-react'
import { Header } from '@/components/Header'
import { ChatMessageItem } from '@/components/ChatMessageItem'
import { DeviceTelemetryWidget } from '@/components/DeviceTelemetryWidget'
import { RecentTicketsList } from '@/components/RecentTicketsList'
import { ChatMessage, DeviceHealthResponse, TicketResponse, ConversationSummary } from '@/types'
import { sendChatMessage, fetchDeviceHealth, fetchRecentTickets, checkSystemHealth, fetchConversations, fetchConversation, reconcileIncident, startConversation, ManualReconciliationError } from '@/services/api'

export const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Describe one IT issue. I can offer knowledge-base guidance and, with your acceptance, create a ServiceNow incident. Device tools use simulated telemetry.',
      timestamp: new Date().toISOString()
    }
  ])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [historyError, setHistoryError] = useState('')
  const [incidentPending, setIncidentPending] = useState(false)
  const [isOpening, setIsOpening] = useState(false)
  const sendLock = useRef(false)
  const openingLock = useRef(false)
  const [servicenowActive, setServicenowActive] = useState(false)
  const [telemetry, setTelemetry] = useState<DeviceHealthResponse | null>(null)
  const [tickets, setTickets] = useState<TicketResponse[]>([])

  const chatBottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchConversations().then(setConversations).catch(() => setHistoryError('Conversation history unavailable.'))
    // Initial data hydration
    checkSystemHealth()
      .then((h) => setServicenowActive(h.servicenow_configured))
      .catch((e) => console.warn('Health check unreachable:', e))

    fetchDeviceHealth('EMP-LT-104')
      .then(setTelemetry)
      .catch((e) => console.warn('Telemetry fetch error:', e))

    fetchRecentTickets()
      .then(setTickets)
      .catch((e) => console.warn('Tickets fetch error:', e))
  }, [])

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  const handleSend = async (messageText: string = input, forceTicket: boolean = false) => {
    const textToSend = messageText.trim()
    if (!textToSend || sendLock.current || openingLock.current) return
    sendLock.current = true

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(7),
      sender: 'user',
      text: textToSend,
      timestamp: new Date().toISOString()
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsSending(true)

    try {
      let activeId = sessionId
      if (!activeId) {
        const started = await startConversation()
        activeId = started.id
        setSessionId(activeId)
      }
      const response = await sendChatMessage(textToSend, activeId, forceTicket)
      setIncidentPending(previous => response.ticket ? false : response.response_type === 'pending_verification' || previous)
      if (response.session_id) {
        setSessionId(response.session_id)
      }

      const assistantMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        sender: 'assistant',
        text: response.message,
        timestamp: response.created_at,
        responseType: response.response_type,
        classification: response.classification,
        ticket: response.ticket,
        sources: response.sources
      }

      setMessages((prev) => [...prev, assistantMsg])
      fetchConversations().then(setConversations).catch(() => setHistoryError('Conversation history unavailable.'))

      // If ticket created, update tickets panel
      if (response.ticket) {
        setTickets((prev) => [response.ticket!, ...prev.filter(t => t.sys_id !== response.ticket!.sys_id)])
      }
    } catch (error) {
      if (error instanceof ManualReconciliationError) {
        setIncidentPending(true)
        setHistoryError(error.message)
      }
      const errorMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        sender: 'assistant',
        text: error instanceof ManualReconciliationError ? error.message : 'The support workflow is unavailable. Reopen this conversation before retrying; an incident may be pending verification.',
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMsg])
      fetchConversations().then(setConversations).catch(() => setHistoryError('Conversation history unavailable.'))
    } finally {
      sendLock.current = false
      setIsSending(false)
    }
  }

  const openConversation = async (id: string) => {
    if (sendLock.current || openingLock.current) return
    openingLock.current = true
    setIsOpening(true)
    setHistoryError('')
    try {
      const saved = await fetchConversation(id)
      setSessionId(saved.id)
      setIncidentPending(saved.incident_status === 'pending')
      const restored: ChatMessage[] = saved.messages.map(m => ({
        id: String(m.id), sender: m.role, text: m.content, timestamp: m.created_at,
        responseType: m.response?.response_type, classification: m.response?.classification,
        ticket: m.response?.ticket, sources: m.response?.sources
      }))
      if (saved.ticket && !restored.some(m => m.ticket?.sys_id === saved.ticket?.sys_id)) {
        restored.push({ id: 'recovered-incident', sender: 'assistant', timestamp: saved.updated_at,
          text: `Incident ${saved.ticket.number} is recorded.`, responseType: 'ticket_created', ticket: saved.ticket })
      }
      setMessages(restored)
    } catch {
      setHistoryError('Unable to open conversation. Please retry.')
    } finally {
      openingLock.current = false
      setIsOpening(false)
    }
  }

  const checkIncident = async () => {
    if (!sessionId || sendLock.current || openingLock.current) return
    sendLock.current = true
    setIsSending(true)
    try {
      const result = await reconcileIncident(sessionId)
      setHistoryError('')
      setIncidentPending(result.status === 'pending')
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(), sender: 'assistant', timestamp: new Date().toISOString(),
        text: result.ticket ? `Incident ${result.ticket.number} is recorded.` : 'Incident creation remains pending verification. Another creation attempt is blocked.',
        responseType: result.ticket ? 'ticket_created' : 'pending_verification', ticket: result.ticket
      }])
      if (result.ticket) setTickets(prev => [result.ticket!, ...prev.filter(t => t.sys_id !== result.ticket!.sys_id)])
    } catch (error) {
      setHistoryError(error instanceof ManualReconciliationError ? error.message : 'Incident verification unavailable. Another creation attempt remains blocked.')
    } finally {
      sendLock.current = false
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header
        servicenowActive={servicenowActive}
        onQuickPrompt={(prompt) => handleSend(prompt)}
      />

      <main className="max-w-7xl w-full mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 items-start">
        {/* Chat Conversation Column */}
        <div className="lg:col-span-2 flex flex-col h-[78vh] rounded-3xl bg-surface/50 border border-border shadow-2xl backdrop-blur-sm overflow-hidden">
          <div className="flex gap-3 items-center p-3 border-b border-border">
            <button disabled={isSending || isOpening} onClick={() => {
              setSessionId(''); setMessages([]); setInput(''); setHistoryError(''); setIncidentPending(false)
            }} className="text-sm text-cyan-300 disabled:opacity-40">New issue</button>
            <select aria-label="Open saved conversation" value={sessionId} disabled={isSending || isOpening}
              onChange={e => { if (e.target.value) openConversation(e.target.value) }}
              className="min-w-0 flex-1 text-sm bg-slate-900 rounded p-2 text-slate-200">
              <option value="">Open a saved conversation</option>
              {conversations.map(c => <option key={c.id} value={c.id}>{c.issue || 'Conversation'}</option>)}
            </select>
          </div>
          {incidentPending && <div role="status" className="p-3 text-sm text-amber-300">
            Incident creation is pending verification.
            <button onClick={checkIncident} disabled={isSending || isOpening} className="ml-2 text-cyan-300 underline">Check incident status</button>
          </div>}
          {historyError && <p role="alert" className="p-3 text-sm text-amber-300">{historyError}</p>}
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-2">
            {messages.map((m) => (
              <ChatMessageItem
                key={m.id}
                message={m}
                onForceEscalate={!isSending && !isOpening && m.id === messages[messages.length - 1]?.id ? () => handleSend('Create a ticket for this issue', true) : undefined}
                onDeclineEscalate={!isSending && !isOpening && m.id === messages[messages.length - 1]?.id ? () => handleSend('No thanks, please do not create a ticket') : undefined}
              />
            ))}

            {isSending && (
              <div className="flex items-center gap-3 my-4 animate-fade-in">
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-blue-400">
                  <Bot className="w-4 h-4 animate-bounce" />
                </div>
                <div className="p-3.5 rounded-2xl rounded-tl-none bg-surface border border-border text-slate-400 text-xs flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                  <span>Processing your support request...</span>
                </div>
              </div>
            )}
            <div ref={chatBottomRef} />
          </div>

          {/* Input Bar */}
          <div className="p-3 md:p-4 border-t border-border bg-surface/80">
            <div className="flex items-center gap-2 bg-slate-900/90 rounded-2xl border border-slate-700/80 px-3.5 py-2 shadow-inner focus-within:border-blue-500/80 transition-all">
              <input
                type="text"
                aria-label="Describe your support issue"
                maxLength={2000}
                disabled={isOpening}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask IT a question, request software, report an issue..."
                className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
              />
              <button
                onClick={() => handleSend()}
                disabled={input.trim().length < 2 || isSending || isOpening}
                className="p-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white disabled:opacity-40 disabled:hover:bg-blue-600 transition-colors shadow-md shadow-blue-500/20"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 px-1">
              <span>Press <strong>Enter</strong> to send</span>
              <span className="flex items-center gap-1 text-slate-400">
                <Sparkles className="w-3 h-3 text-cyan-400" /> Grounded in enterprise documentation
              </span>
            </div>
          </div>
        </div>

        {/* Sidebar Column: Telemetry & Active Tickets */}
        <div className="space-y-6">
          <DeviceTelemetryWidget
            telemetry={telemetry}
            onTelemetryUpdated={setTelemetry}
          />
          <RecentTicketsList tickets={tickets} />
        </div>
      </main>
    </div>
  )
}

export default App
