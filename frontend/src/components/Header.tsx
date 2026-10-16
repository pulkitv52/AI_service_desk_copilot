import React from 'react'
import { Bot, Shield, Database, Sparkles } from 'lucide-react'

interface HeaderProps {
  servicenowActive: boolean
  onQuickPrompt: (prompt: string) => void
}

export const Header: React.FC<HeaderProps> = ({ servicenowActive, onQuickPrompt }) => {
  const quickPrompts = [
    { label: 'Reset Password', prompt: 'I forgot my password. How can I reset it?' },
    { label: 'VPN Issue', prompt: 'My GlobalProtect VPN is not connecting.' },
    { label: 'Low Disk Space', prompt: 'My laptop says disk space is almost full.' },
    { label: 'Install VS Code', prompt: 'I need VS Code installed on my machine.' },
    { label: 'SAP PO Approval', prompt: 'SAP is not allowing me to approve purchase orders. Steps failed, please escalate.' }
  ]

  return (
    <header className="border-b border-border bg-surface/70 backdrop-blur-md sticky top-0 z-20 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold tracking-tight text-white">AI Service Desk Copilot</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Zero-L1
              </span>
            </div>
            <p className="text-xs text-slate-400">Enterprise Support Orchestrator with RAG & Simulated Device Tools</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-surfaceLight border border-border text-slate-300">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>Knowledge store: <strong>PostgreSQL</strong></span>
          </div>
          <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-surfaceLight border border-border text-slate-300">
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
            <span>ITSM: <strong className={servicenowActive ? 'text-emerald-400' : 'text-amber-400'}>
              {servicenowActive ? 'ServiceNow PDI' : 'Mock Ticketing'}
            </strong></span>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto mt-3 flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-xs text-slate-400 shrink-0 font-medium">Quick Scenarios:</span>
        {quickPrompts.map((q) => (
          <button
            key={q.label}
            onClick={() => onQuickPrompt(q.prompt)}
            className="text-xs whitespace-nowrap px-3 py-1 rounded-full bg-surfaceLight hover:bg-slate-700 text-slate-300 hover:text-white border border-border transition-all duration-150"
          >
            {q.label}
          </button>
        ))}
      </div>
    </header>
  )
}
