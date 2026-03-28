'use client'

import { Layers } from 'lucide-react'

export default function Blueprints() {
  return (
    <div className="p-8 bg-[#080808] min-h-full">
      <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Blueprint Analysis</h1>
      <p className="text-zinc-400">Phase 4 -- Upload PDFs for AI fixture detection and takeoff generation.</p>
      <div className="mt-8 glass-card p-12 text-center">
        <div className="w-16 h-16 bg-gradient-to-br from-blue-500/20 to-violet-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-white/[0.06]">
          <Layers size={32} className="text-blue-400" />
        </div>
        <h2 className="text-xl font-semibold text-zinc-200 mb-2">Coming in Phase 4</h2>
        <p className="text-zinc-500 max-w-md mx-auto">
          Upload plumbing blueprints (PDFs) and AI will detect fixtures, count items,
          and generate a complete material takeoff automatically.
        </p>
      </div>
    </div>
  )
}
