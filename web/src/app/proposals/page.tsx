'use client'

import { FileOutput } from 'lucide-react'

export default function Proposals() {
  return (
    <div className="p-8 bg-[#080808] min-h-full">
      <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Proposals</h1>
      <p className="text-zinc-400">Phase 2 -- Generate professional PDF proposals for customers.</p>
      <div className="mt-8 glass-card p-12 text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-blue-500/20 to-violet-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/[0.06]">
          <FileOutput size={32} className="text-blue-400" />
        </div>
        <h2 className="text-xl font-semibold text-zinc-200 mb-2">Coming in Phase 2</h2>
        <p className="text-zinc-500 max-w-md mx-auto">
          Auto-generate branded PDF proposals from estimates. Include material specs,
          labor breakdown, terms and signature fields.
        </p>
      </div>
    </div>
  )
}
