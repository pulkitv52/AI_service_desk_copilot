import React from 'react'
import { Ticket } from 'lucide-react'
import { TicketResponse } from '@/types'

interface RecentTicketsListProps {
  tickets: TicketResponse[]
}

export const RecentTicketsList: React.FC<RecentTicketsListProps> = ({ tickets }) => {
  if (tickets.length === 0) {
    return (
      <div className="rounded-2xl bg-surface border border-border p-4 shadow-lg text-center text-xs text-slate-500">
        <Ticket className="w-5 h-5 mx-auto mb-1.5 opacity-40" />
        No incident tickets created yet.
      </div>
    )
  }

  return (
    <div className="rounded-2xl bg-surface border border-border p-4 shadow-lg">
      <div className="flex items-center justify-between pb-2.5 border-b border-border mb-3">
        <div className="flex items-center gap-2">
          <Ticket className="w-4 h-4 text-blue-400" />
          <h2 className="text-xs font-semibold text-white tracking-wide uppercase">Active Incident Tickets</h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/30">
          {tickets.length} total
        </span>
      </div>

      <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
        {tickets.map((t) => (
          <div
            key={t.sys_id}
            className="p-2.5 rounded-xl bg-slate-900/70 border border-slate-800 text-xs hover:border-slate-700 transition-colors"
          >
            <div className="flex items-center justify-between gap-1 mb-1">
              <span className="font-mono font-bold text-white tracking-wide">{t.number}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                {t.priority || 'P3'}
              </span>
            </div>
            <p className="text-slate-300 line-clamp-1 mb-1 font-medium">{t.short_description}</p>
            <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/80">
              <span>{t.assignment_group || 'Service Desk L1'}</span>
              <span className="uppercase text-slate-400">{t.provider}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
