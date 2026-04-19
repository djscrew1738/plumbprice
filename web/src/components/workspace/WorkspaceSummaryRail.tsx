'use client'

import { AnimatePresence, motion } from 'framer-motion'
import { ChevronUp, DollarSign, X } from 'lucide-react'
import { EstimateBreakdown } from '../estimator/EstimateBreakdown'
import { formatCurrency } from '@/lib/utils'
import type { ChatMessage } from '@/types'

interface WorkspaceSummaryRailProps {
  county: string
  selectedEstimate: ChatMessage | null
  sheetOpen: boolean
  onSheetOpenChange: (open: boolean) => void
}

export function WorkspaceSummaryRail({
  county,
  selectedEstimate,
  sheetOpen,
  onSheetOpenChange,
}: WorkspaceSummaryRailProps) {
  const estimate = selectedEstimate?.estimate

  return (
    <>
      <aside className="hidden w-[360px] shrink-0 lg:flex">
        <div className="shell-panel flex min-h-0 w-full flex-col overflow-hidden">
          {estimate ? (
            <EstimateBreakdown
              estimate={estimate}
              confidenceLabel={selectedEstimate.confidence_label || 'HIGH'}
              confidenceScore={selectedEstimate.confidence || 0}
              assumptions={selectedEstimate.assumptions || []}
              county={county}
              savedEstimateId={selectedEstimate.estimate_id}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center px-7 text-center">
              <div className="mb-3 flex size-12 items-center justify-center rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)]">
                <DollarSign size={20} className="text-[color:var(--muted-ink)]" />
              </div>
              <h2 className="text-sm font-semibold text-[color:var(--ink)]">Estimate summary</h2>
              <p className="mt-1 max-w-[220px] text-xs text-[color:var(--muted-ink)]">
                Ask a pricing question to populate totals and assumptions.
              </p>
            </div>
          )}
        </div>
      </aside>

      <AnimatePresence>
        {estimate && !sheetOpen && (
          <motion.button
            type="button"
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            whileTap={{ scale: 0.96 }}
            onClick={() => onSheetOpenChange(true)}
            className="fixed bottom-[76px] right-4 z-30 inline-flex items-center gap-2 rounded-2xl bg-[color:var(--accent)] px-4 py-2.5 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(183,96,43,0.35)] lg:hidden"
            aria-label={`View total ${formatCurrency(estimate.grand_total)}`}
          >
            <DollarSign size={15} />
            {formatCurrency(estimate.grand_total)}
            <ChevronUp size={14} className="opacity-75" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {sheetOpen && estimate && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm lg:hidden"
              onClick={() => onSheetOpenChange(false)}
            />
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Estimate summary sheet"
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 28, stiffness: 320 }}
              className="fixed inset-x-0 bottom-0 z-50 px-3 pb-[max(env(safe-area-inset-bottom),12px)] pt-6 lg:hidden"
              onClick={() => onSheetOpenChange(false)}
            >
              <div
                className="bottom-sheet mx-auto flex w-full max-w-lg flex-col overflow-hidden"
                style={{ maxHeight: '87dvh' }}
                onClick={event => event.stopPropagation()}
              >
                <div className="flex items-center justify-center pt-3 pb-1">
                  <div className="h-1.5 w-11 rounded-full bg-[color:var(--line)]" />
                </div>
                <div className="flex items-center justify-between border-b border-[color:var(--line)] px-5 py-3">
                  <span className="text-sm font-semibold text-[color:var(--ink)]">Estimate summary</span>
                  <button
                    type="button"
                    className="rounded-xl p-2 text-[color:var(--muted-ink)] transition-colors hover:bg-[color:var(--panel-strong)] hover:text-[color:var(--ink)]"
                    onClick={() => onSheetOpenChange(false)}
                    aria-label="Close summary"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto">
                  <EstimateBreakdown
                    estimate={estimate}
                    confidenceLabel={selectedEstimate.confidence_label || 'HIGH'}
                    confidenceScore={selectedEstimate.confidence || 0}
                    assumptions={selectedEstimate.assumptions || []}
                    county={county}
                    savedEstimateId={selectedEstimate.estimate_id}
                    compact
                  />
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
