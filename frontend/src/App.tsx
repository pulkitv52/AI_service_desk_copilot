import React, { useState, useEffect, useRef } from 'react'
import { Send, Bot, Sparkles, RefreshCw } from 'lucide-react'
import { Header } from '@/components/Header'
import { ChatMessageItem } from '@/components/ChatMessageItem'
import { DeviceTelemetryWidget } from '@/components/DeviceTelemetryWidget'
import { RecentTicketsList } from '@/components/RecentTicketsList'
import { ChatMessage, DeviceHealthResponse, TicketResponse } from '@/types'
import { sendChatMessage, fetchDeviceHealth, fetchRecentTickets, checkSystemHealth } from '@/services/api'

export const App: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: 'Hello! I am your AI Service Desk Copilot.\n\nI can resolve IT issues, provide self-service knowledge base guidance, run safe diagnostics on your endpoint, or escalate directly to ServiceNow support teams. How can I assist you today?',
      timestamp: new Date().toISOString()
    }
  ])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')
  const [servicenowActive, setServicenowActive] = useState(false)
  const [telemetry, setTelemetry] = useState<DeviceHealthResponse | null>(null)
  const [tickets, setTickets] = useState<TicketResponse[]>([])

  const chatBottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
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
    if (!textToSend || isSending) return

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
      const response = await sendChatMessage(textToSend, sessionId || undefined, forceTicket)
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

      // If ticket created, update tickets panel
      if (response.ticket) {
        setTickets((prev) => [response.ticket!, ...prev])
      }
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: Math.random().toString(36).substring(7),
        sender: 'assistant',
        text: 'Sorry, I encountered an issue communicating with the Service Desk backend. Please verify the service is running.',
        timestamp: new Date().toISOString()
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
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
          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-2">
            {messages.map((m) => (
              <ChatMessageItem
                key={m.id}
                message={m}
                onForceEscalate={() => handleSend('Create a ticket for this issue', true)}
              />
            ))}

            {isSending && (
              <div className="flex items-center gap-3 my-4 animate-fade-in">
                <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-blue-400">
                  <Bot className="w-4 h-4 animate-bounce" />
                </div>
                <div className="p-3.5 rounded-2xl rounded-tl-none bg-surface border border-border text-slate-400 text-xs flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                  <span>Classifying intent & consulting pgvector knowledge base...</span>
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
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask IT a question, request software, report an issue..."
                className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isSending}
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
