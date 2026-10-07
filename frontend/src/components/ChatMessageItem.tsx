import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, User, BookOpen, CheckCircle2, Ticket } from 'lucide-react'
import { ChatMessage, TicketPriority } from '@/types'

interface ChatMessageItemProps {
  message: ChatMessage
  onForceEscalate?: () => void
}

const priorityColors: Record<TicketPriority, string> = {
  P1: 'bg-red-500/10 text-red-400 border-red-500/30',
  P2: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  P3: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  P4: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({ message, onForceEscalate }) => {
  const isUser = message.sender === 'user'

  return (
    <div className={`flex gap-3 my-4 animate-fade-in ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${
        isUser
          ? 'bg-gradient-to-tr from-cyan-600 to-blue-500 text-white'
          : 'bg-slate-800 border border-slate-700 text-blue-400 shadow-md'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl p-4 ${
        isUser
          ? 'bg-blue-600 text-white rounded-tr-none'
          : 'bg-surface border border-border text-slate-200 rounded-tl-none shadow-sm'
      }`}>
        {!isUser && message.classification && (
          <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-slate-800 text-xs">
            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono text-cyan-400">
              {message.classification.intent.replace('_', ' ').toUpperCase()}
            </span>

            {message.classification.application && (
              <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                App: {message.classification.application}
              </span>
            )}

            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-400">
              Routed to: <strong className="text-slate-200">{message.classification.assignment_group}</strong>
            </span>

            <span className={`px-2 py-0.5 rounded border font-semibold ${priorityColors[message.classification.priority] || priorityColors.P3}`}>
              {message.classification.priority}
            </span>
          </div>
        )}

        <div className="text-sm leading-relaxed font-sans">
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.text}</div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-2.5 last:mb-0 leading-relaxed text-slate-200">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                em: ({ children }) => <em className="italic text-slate-300">{children}</em>,
                ul: ({ children }) => <ul className="list-disc list-outside ml-5 mb-2.5 space-y-1 text-slate-200">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-outside ml-5 mb-2.5 space-y-1.5 text-slate-200">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed pl-0.5">{children}</li>,
                code: ({ children, className, ...props }) => (
                  <code className="bg-slate-900/90 text-cyan-300 px-1.5 py-0.5 rounded font-mono text-xs border border-slate-700/70" {...props}>
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 my-2.5 overflow-x-auto text-xs font-mono text-slate-200 shadow-inner">
                    {children}
                  </pre>
                ),
                a: ({ href, children }) => (
                  <a href={href} target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline underline-offset-2">
                    {children}
                  </a>
                ),
              }}
            >
              {message.text}
            </ReactMarkdown>
          )}
        </div>

        {/* Ticket Created Card */}
        {message.ticket && (
          <div className="mt-3 p-3.5 rounded-xl bg-slate-900/90 border border-blue-500/30 shadow-inner">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <Ticket className="w-4 h-4 text-blue-400" />
                <span className="font-semibold text-white tracking-wide">{message.ticket.number}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Created ({message.ticket.provider.toUpperCase()})
                </span>
              </div>
              <span className="text-xs font-mono text-slate-400">P3 Medium</span>
            </div>

            <div className="text-xs text-slate-300 grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-800">
              <div>
                <span className="text-slate-500">Group: </span>
                <span className="text-white font-medium">{message.ticket.assignment_group || 'Service Desk L1'}</span>
              </div>
              <div>
                <span className="text-slate-500">Sys ID: </span>
                <span className="font-mono text-slate-400">{message.ticket.sys_id.slice(0, 12)}...</span>
              </div>
            </div>
          </div>
        )}

        {/* Grounded Knowledge Sources Box */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-slate-800">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1.5">
              <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
              <span>Grounded Knowledge Base Sources:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((src) => (
                <span
                  key={src}
                  className="text-xs px-2.5 py-1 rounded-md bg-slate-900 text-cyan-300 border border-slate-800 font-mono"
                >
                  {src}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Escalation Button if deflected and user wants a ticket */}
        {!isUser && message.responseType === 'deflected_rag' && onForceEscalate && (
          <div className="mt-3 pt-2 flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> Deflected by RAG
            </span>
            <button
              onClick={onForceEscalate}
              className="hover:text-blue-400 underline decoration-slate-600 transition-colors"
            >
              Didn't help? Open a Ticket
            </button>
          </div>
        )}

        <div className="mt-2 text-[10px] text-slate-500 text-right">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}
