'use client'

import { useState } from 'react'
import { agentTraceApiV3 } from '@/lib/api-v3'
import { Search, Clock, Wrench } from 'lucide-react'


export default function AgentTracesAdminPage() {
  const [estimateId, setEstimateId] = useState('')
  const [trace, setTrace] = useState<{
    estimate_id: number
    agent_trace: Record<string, unknown>
    market_adjustment_applied: number
    confidence_components: Record<string, number>
    tool_calls: Array<{
      tool_name: string
      arguments: unknown
      result: unknown
      latency_ms: number
      created_at: string
    }>
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSearch() {
    if (!estimateId.trim()) return
    try {
      setLoading(true)
      setError('')
      const res = await agentTraceApiV3.getEstimateTrace(Number(estimateId))
      setTrace(res.data)
    } catch {
      setError('Trace not found or access denied')
      setTrace(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-[color:var(--ink)] mb-1">Agent Traces</h1>
      <p className="text-sm text-[color:var(--muted-ink)] mb-6">
        Inspect how the v3 agent reasoned about and priced an estimate.
      </p>

      <div className="flex gap-2 mb-6">
        <input
          type="number"
          value={estimateId}
          onChange={e => setEstimateId(e.target.value)}
          placeholder="Enter estimate ID"
          className="flex-1 rounded-lg border border-[color:var(--line)] bg-[color:var(--panel)] px-4 py-2 text-sm text-[color:var(--ink)] placeholder:text-[color:var(--muted-ink)]"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="rounded-lg bg-[color:var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 inline-flex items-center gap-1.5"
        >
          <Search size={16} />
          {loading ? 'Loading...' : 'Inspect'}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {trace && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-5">
            <h3 className="text-sm font-semibold text-[color:var(--ink)] mb-3">Trace Summary</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-lg bg-[color:var(--panel)] p-3">
                <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Classified By</div>
                <div className="text-sm font-semibold text-[color:var(--ink)] mt-1">
                  {String(trace.agent_trace.classified_by ?? 'unknown')}
                </div>
              </div>
              <div className="rounded-lg bg-[color:var(--panel)] p-3">
                <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Total Latency</div>
                <div className="text-sm font-semibold text-[color:var(--ink)] mt-1">
                  {typeof trace.agent_trace.total_latency_ms === 'number' ? `${trace.agent_trace.total_latency_ms}ms` : 'N/A'}
                </div>
              </div>
              <div className="rounded-lg bg-[color:var(--panel)] p-3">
                <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Market Factor</div>
                <div className="text-sm font-semibold text-[color:var(--ink)] mt-1">
                  ×{trace.market_adjustment_applied.toFixed(4)}
                </div>
              </div>
              <div className="rounded-lg bg-[color:var(--panel)] p-3">
                <div className="text-[10px] uppercase tracking-wider text-[color:var(--muted-ink)]">Tool Calls</div>
                <div className="text-sm font-semibold text-[color:var(--ink)] mt-1">
                  {trace.tool_calls.length}
                </div>
              </div>
            </div>
          </div>

          {/* Reasoning */}
          {typeof trace.agent_trace.classification_reasoning === 'string' && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">Classification Reasoning</h3>
              <p className="text-sm text-amber-800 leading-relaxed">
                {trace.agent_trace.classification_reasoning}
              </p>
            </div>
          )}

          {/* Tool Calls */}
          {trace.tool_calls.length > 0 && (
            <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] overflow-hidden">
              <div className="px-5 py-3 border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                <h3 className="text-sm font-semibold text-[color:var(--ink)]">Tool Calls</h3>
              </div>
              <div className="divide-y divide-[color:var(--line)]">
                {trace.tool_calls.map((tc, i) => (
                  <div key={i} className="px-5 py-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Wrench size={14} className="text-[color:var(--accent)]" />
                      <span className="text-sm font-medium text-[color:var(--ink)]">{tc.tool_name}</span>
                      <span className="ml-auto text-xs text-[color:var(--muted-ink)] flex items-center gap-1">
                        <Clock size={12} />
                        {tc.latency_ms}ms
                      </span>
                    </div>
                    {tc.arguments != null && (
                      <pre className="mt-1 rounded bg-[color:var(--panel-strong)] p-2 text-[11px] text-[color:var(--muted-ink)] overflow-auto">
                        {JSON.stringify(tc.arguments, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw Trace */}
          <div className="rounded-xl border border-[color:var(--line)] bg-[color:var(--panel)] overflow-hidden">
            <div className="px-5 py-3 border-b border-[color:var(--line)] bg-[color:var(--panel-strong)]">
              <h3 className="text-sm font-semibold text-[color:var(--ink)]">Raw Agent Trace</h3>
            </div>
            <pre className="p-4 text-[11px] text-[color:var(--muted-ink)] overflow-auto">
              {JSON.stringify(trace.agent_trace, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
