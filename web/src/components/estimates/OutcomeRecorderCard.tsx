'use client'

import { motion } from 'framer-motion'

export interface SentProposal {
  id: number
  recipient_email: string
  recipient_name: string | null
  sent_at: string | null
  created_at: string
}

export interface OutcomeRecorderCardProps {
  assumptions: string[]
  sentProposals: SentProposal[]
}

export function OutcomeRecorderCard({
  assumptions,
  sentProposals,
}: OutcomeRecorderCardProps) {
  return (
    <>
      {/* Assumptions */}
      {assumptions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.15 }}
          className="card p-4"
        >
          <h2 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Assumptions</h2>
          <ul className="space-y-2">
            {assumptions.map((a, i) => (
              <li key={i} className="flex items-start gap-2.5 text-xs text-zinc-500">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-700 mt-1.5 shrink-0" />
                {a}
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Sent Proposals */}
      {sentProposals.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: 0.2 }}
          className="card p-4"
        >
          <h2 className="text-xs font-bold text-white uppercase tracking-wider mb-3">Sent Proposals</h2>
          <ul className="space-y-2">
            {sentProposals.map(p => (
              <li key={p.id} className="flex items-center justify-between text-xs">
                <span className="text-[color:var(--foreground)]">
                  {p.recipient_name ? `${p.recipient_name} <${p.recipient_email}>` : p.recipient_email}
                </span>
                <span className="text-[color:var(--muted-ink)] shrink-0 ml-4">
                  {p.sent_at
                    ? new Date(p.sent_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                    : new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                  }
                </span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </>
  )
}
