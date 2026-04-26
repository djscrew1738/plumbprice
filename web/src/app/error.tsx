'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Droplets, RotateCcw, Home } from 'lucide-react'
import { BrandFooter } from '@/components/layout/BrandFooter'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, rgba(220,38,38,0.08) 0%, transparent 70%)' }}
        />
      </div>

      <div className="w-full max-w-sm text-center">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-600/30 mb-4">
            <Droplets size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">PlumbPrice AI</h1>
        </div>

        <div className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-8 shadow-2xl">
          <h2 className="text-xl font-bold text-white mb-2">Something went wrong</h2>
          <p className="text-sm text-zinc-500 mb-4">
            An unexpected error occurred. You can try again or return home.
          </p>

          {error.message && (
            <details className="mb-6 text-left">
              <summary className="cursor-pointer text-xs text-zinc-600 hover:text-zinc-400 transition-colors select-none">
                Error details
              </summary>
              <pre className="mt-2 rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-2 text-[11px] text-zinc-500 overflow-x-auto whitespace-pre-wrap break-all">
                {error.message}
                {error.digest ? `\nDigest: ${error.digest}` : ''}
              </pre>
            </details>
          )}

          <div className="flex gap-3">
            <button
              onClick={reset}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/[0.08] transition-colors"
            >
              <RotateCcw size={14} />
              Try Again
            </button>
            <button
              onClick={() => router.push('/')}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-colors"
            >
              <Home size={14} />
              Go Home
            </button>
          </div>
        </div>

        <BrandFooter className="mt-5" />
      </div>
    </div>
  )
}
