'use client'

import { FileText, Brain, Award, Sparkles } from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import { Badge } from '@/components/ui/Badge'
import { formatCurrencyDecimal } from '@/lib/utils'
import type { LineItem } from './LineItemsTable'

interface Props {
  item: LineItem | null
  onClose: () => void
}

const KIND_LABEL: Record<string, string> = {
  preference: 'Preference',
  profile: 'Profile',
  customer: 'Customer',
  job_history: 'Job history',
  fact: 'Fact',
}

export function WhyThisPriceModal({ item, onClose }: Props) {
  const open = item !== null
  const trace = (item?.trace_json ?? {}) as Record<string, unknown>

  const ragSources = (trace.rag_sources as Array<{ doc_name: string; score: number }>) ?? []
  const memoryHits = (trace.memory_hits as Array<{ id: number; kind: string; score: number | null }>) ?? []
  const similarOutcomes = (trace.similar_outcomes as Array<{ estimate_id: number; outcome: string; price: number | null }>) ?? []
  const taskCode = trace.task_code as string | undefined
  const assemblyCode = trace.assembly_code as string | undefined
  const county = trace.county as string | undefined
  const supplier = trace.supplier as string | undefined
  const leadRate = trace.lead_rate as number | undefined
  const adjustedHours = trace.adjusted_hours as number | undefined
  const sourceFile = trace.source_file as string | undefined
  const reasoning = trace.reasoning as string | undefined

  const hasAnySignal =
    ragSources.length > 0 ||
    memoryHits.length > 0 ||
    similarOutcomes.length > 0 ||
    taskCode ||
    leadRate ||
    sourceFile ||
    reasoning

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Why this price?"
      description={item?.description ?? ''}
      size="lg"
    >
      {!hasAnySignal ? (
        <p className="text-sm text-[color:var(--muted-ink)]">
          No additional context recorded for this line item.
        </p>
      ) : (
        <div className="space-y-5">
          {item && (
            <section>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                Pricing breakdown
              </h4>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-[color:var(--muted-ink)]">Quantity</dt>
                <dd>{item.quantity} {item.unit}</dd>
                <dt className="text-[color:var(--muted-ink)]">Unit cost</dt>
                <dd className="tabular-nums">{formatCurrencyDecimal(item.unit_cost)}</dd>
                <dt className="text-[color:var(--muted-ink)]">Total</dt>
                <dd className="tabular-nums font-semibold">{formatCurrencyDecimal(item.total_cost)}</dd>
                {item.supplier && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">Supplier</dt>
                    <dd>{item.supplier}</dd>
                  </>
                )}
                {item.sku && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">SKU</dt>
                    <dd className="font-mono text-xs">{item.sku}</dd>
                  </>
                )}
                {leadRate && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">Lead rate</dt>
                    <dd className="tabular-nums">${leadRate}/hr</dd>
                  </>
                )}
                {adjustedHours && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">Adjusted hours</dt>
                    <dd className="tabular-nums">{adjustedHours}</dd>
                  </>
                )}
                {county && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">County</dt>
                    <dd>{county}</dd>
                  </>
                )}
                {(taskCode || assemblyCode) && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">Template</dt>
                    <dd className="font-mono text-xs">{taskCode}{assemblyCode ? ` / ${assemblyCode}` : ''}</dd>
                  </>
                )}
                {supplier && !item.supplier && (
                  <>
                    <dt className="text-[color:var(--muted-ink)]">Pricing supplier</dt>
                    <dd>{supplier}</dd>
                  </>
                )}
              </dl>
            </section>
          )}

          {reasoning && (
            <section>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                <Sparkles size={12} /> AI reasoning
              </h4>
              <p className="text-sm text-[color:var(--ink)] whitespace-pre-wrap">{reasoning}</p>
            </section>
          )}

          {memoryHits.length > 0 && (
            <section>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                <Brain size={12} /> Learned facts about your business ({memoryHits.length})
              </h4>
              <ul className="space-y-1.5 text-sm">
                {memoryHits.map((m, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Badge variant="info" size="sm">{KIND_LABEL[m.kind] ?? m.kind}</Badge>
                    <span className="text-[color:var(--ink)]">memory #{m.id}</span>
                    {m.score !== null && (
                      <span className="text-xs text-[color:var(--muted-ink)] tabular-nums">
                        relevance {Math.round(m.score * 100)}%
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {similarOutcomes.length > 0 && (
            <section>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                <Award size={12} /> Similar past jobs ({similarOutcomes.length})
              </h4>
              <ul className="space-y-1.5 text-sm">
                {similarOutcomes.map((o, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <Badge
                      variant={o.outcome === 'won' ? 'success' : o.outcome === 'lost' ? 'danger' : 'neutral'}
                      size="sm"
                    >
                      {o.outcome}
                    </Badge>
                    <span className="text-[color:var(--ink)]">Estimate #{o.estimate_id}</span>
                    {o.price && (
                      <span className="tabular-nums text-[color:var(--muted-ink)]">
                        ${Math.round(o.price).toLocaleString()}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {ragSources.length > 0 && (
            <section>
              <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                <FileText size={12} /> Reference documents ({ragSources.length})
              </h4>
              <ul className="space-y-1.5 text-sm">
                {ragSources.map((s, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="text-[color:var(--ink)] truncate">{s.doc_name}</span>
                    <span className="text-xs text-[color:var(--muted-ink)] tabular-nums shrink-0">
                      match {Math.round((s.score ?? 0) * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {sourceFile && (
            <section>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-[color:var(--muted-ink)] mb-2">
                Source
              </h4>
              <p className="text-sm font-mono text-[color:var(--ink)]">{sourceFile}</p>
            </section>
          )}
        </div>
      )}
    </Modal>
  )
}
