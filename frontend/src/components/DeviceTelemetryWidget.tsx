import React, { useState } from 'react'
import { HardDrive, Activity, Wifi, RefreshCw, Wrench, ShieldCheck, Check } from 'lucide-react'
import { DeviceHealthResponse, RemediationResultResponse } from '@/types'
import { triggerDeviceRemediation } from '@/services/api'

interface DeviceTelemetryWidgetProps {
  telemetry: DeviceHealthResponse | null
  onTelemetryUpdated: (updated: DeviceHealthResponse) => void
}

export const DeviceTelemetryWidget: React.FC<DeviceTelemetryWidgetProps> = ({
  telemetry,
  onTelemetryUpdated,
}) => {
  const [dryRun, setDryRun] = useState(false)
  const [loadingTool, setLoadingTool] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<RemediationResultResponse | null>(null)

  if (!telemetry) {
    return (
      <div className="p-4 rounded-xl bg-surface border border-border animate-pulse">
        <div className="h-4 bg-slate-800 rounded w-1/3 mb-2"></div>
        <div className="h-20 bg-slate-800 rounded"></div>
      </div>
    )
  }

  const handleRemediate = async (toolName: string) => {
    try {
      setLoadingTool(toolName)
      setLastResult(null)
      const res = await triggerDeviceRemediation(telemetry.device_id, toolName, dryRun)
      setLastResult(res)
      if (!dryRun) {
        onTelemetryUpdated({
          ...telemetry,
          ...(res.after_state as unknown as DeviceHealthResponse),
        })
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoadingTool(null)
    }
  }

  const diskPercent = Math.round((telemetry.disk_free_gb / telemetry.disk_total_gb) * 100)
  const isDiskLow = telemetry.disk_free_gb < 10.0

  return (
    <div className="rounded-2xl bg-surface border border-border p-4 shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-xs font-semibold text-white tracking-wide uppercase">Synthetic DEX Telemetry</h2>
        </div>
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase border font-semibold ${
          telemetry.health_status === 'healthy'
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            : telemetry.health_status === 'warning'
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            : 'bg-red-500/10 text-red-400 border-red-500/30 animate-pulse'
        }`}>
          {telemetry.health_status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 my-3 text-xs">
        <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1.5"><HardDrive className="w-3.5 h-3.5 text-blue-400" /> Free Disk</span>
            <span className={`font-mono font-bold ${isDiskLow ? 'text-red-400' : 'text-slate-200'}`}>
              {telemetry.disk_free_gb.toFixed(1)} GB
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${isDiskLow ? 'bg-red-500' : 'bg-emerald-500'}`}
              style={{ width: `${Math.min(100, diskPercent)}%` }}
            ></div>
          </div>
          <span className="text-[10px] text-slate-500 mt-1 block">{diskPercent}% of {telemetry.disk_total_gb} GB</span>
        </div>

        <div className="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 mb-1">
            <span className="flex items-center gap-1.5"><Wifi className="w-3.5 h-3.5 text-cyan-400" /> Latency</span>
            <span className="font-mono font-bold text-slate-200">{telemetry.network_latency_ms} ms</span>
          </div>
          <span className="text-[10px] text-slate-500 block">VPN: {telemetry.vpn_connected ? 'Connected' : 'Disconnected'}</span>
          <span className="text-[10px] text-slate-500 block">Host: {telemetry.hostname}</span>
        </div>
      </div>

      {/* Self-Healing Controls */}
      <div className="pt-2 border-t border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1">
            <Wrench className="w-3.5 h-3.5 text-amber-400" /> Safe Self-Healing Tools
          </span>
          <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-blue-500 focus:ring-0 w-3 h-3"
            />
            Dry Run
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleRemediate('clean_temp_files')}
            disabled={loadingTool !== null}
            className="text-xs py-1.5 px-2.5 rounded-lg bg-surfaceLight hover:bg-slate-700 text-slate-200 hover:text-white border border-border flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
          >
            {loadingTool === 'clean_temp_files' ? (
              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
            ) : (
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
            )}
            Clean Temp Files
          </button>

          <button
            onClick={() => handleRemediate('purge_developer_caches')}
            disabled={loadingTool !== null}
            className="text-xs py-1.5 px-2.5 rounded-lg bg-surfaceLight hover:bg-slate-700 text-slate-200 hover:text-white border border-border flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
          >
            {loadingTool === 'purge_developer_caches' ? (
              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
            ) : (
              <ShieldCheck className="w-3 h-3 text-cyan-400" />
            )}
            Purge Dev Caches
          </button>
        </div>

        {/* Remediation Action Feedback Banner */}
        {lastResult && (
          <div className="mt-2.5 p-2 rounded-lg bg-slate-900 border border-border text-[11px] animate-fade-in">
            <div className="flex items-center gap-1.5 font-semibold text-emerald-400 mb-0.5">
              <Check className="w-3 h-3" />
              <span>{lastResult.dry_run ? 'Dry-Run Simulation Complete' : 'Remediation Executed'}</span>
            </div>
            <p className="text-slate-300">{lastResult.output}</p>
          </div>
        )}
      </div>
    </div>
  )
}
