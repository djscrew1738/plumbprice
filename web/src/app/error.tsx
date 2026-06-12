'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Droplets, RotateCcw, Home, Copy, Check } from 'lucide-react'
import { BrandFooter } from '@/components/layout/BrandFooter'
import { Button } from '@/components/ui/Button'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  useEffect(() => {
    // In production, send to Sentry instead of console.error to avoid leaking
    // component stacks and file paths to the browser console.
    if (process.env.NODE_ENV === 'development') {
      console.error('Root error.tsx caught:', error)
    }
  }, [error])

  return (
    <div className="min-h-dvh bg-[color:var(--canvas)] flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, hsl(var(--danger) / 0.08) 0%, transparent 70%)' }}
        />
      </div>

      <div className="w-full max-w-sm text-center">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] rounded-2xl flex items-center justify-center shadow-[0_4px_20px_var(--accent-glow)] mb-4">
            <Droplets size={26} className="text-[color:var(--ink-inverse)]" />
          </div>
          <h1 className="text-2xl font-extrabold text-[color:var(--ink)] tracking-tight">PlumbPrice AI</h1>
        </div>

        <div className="shell-panel p-8">
          <h2 className="text-xl font-bold text-[color:var(--ink)] mb-2">Something went wrong</h2>
          <p className="text-sm text-[color:var(--muted-ink)] mb-4">
            An unexpected error occurred. You can try again or return home.
          </p>

          {error.message && (
            <details className="mb-6 text-left">
              <summary className="cursor-pointer text-xs text-[color:var(--muted-ink)] hover:text-[color:var(--ink-secondary)] transition-colors select-none">
                Error details
              </summary>
              <pre className="mt-2 rounded-xl bg-[color:var(--panel-strong)] border border-[color:var(--line)] px-3 py-2 text-[11px] text-[color:var(--ink-secondary)] overflow-x-auto whitespace-pre-wrap break-all">
                {error.message}
                {error.digest ? `\nDigest: ${error.digest}` : ''}
              </pre>
            </details>
          )}

          <div className="flex gap-3">
            <Button
              variant="secondary"
              onClick={reset}
              className="flex-1"
            >
              <RotateCcw size={14} />
              Try Again
            </Button>
            <Button
              variant="primary"
              onClick={() => router.push('/')}
              className="flex-1"
            >
              <Home size={14} />
              Go Home
            </Button>
          </div>

          {error.message && (
            <ErrorDetails error={error} />
          )}
        </div>

        <BrandFooter className="mt-5" />
      </div>
    </div>
  )
}

function ErrorDetails({ error }: { error: Error & { digest?: string } }) {
  const [copied, setCopied] = useState(false)
  const details = `${error.message}${error.digest ? `\nDigest: ${error.digest}` : ''}`

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(details)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  return (
    <details className="mt-4 text-left">
      <summary className="cursor-pointer text-xs text-[color:var(--muted-ink)] hover:text-[color:var(--ink-secondary)] transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)] rounded-lg px-1 -ml-1">
        Error details
      </summary>
      <div className="relative mt-2">
        <pre className="rounded-xl bg-[color:var(--panel-strong)] border border-[color:var(--line)] px-3 py-2 text-[11px] text-[color:var(--ink-secondary)] overflow-x-auto whitespace-pre-wrap break-all pr-10">
          {details}
        </pre>
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 rounded-lg p-1.5 text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] hover:bg-[color:var(--panel)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--accent)]"
          aria-label={copied ? 'Copied!' : 'Copy error details'}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
        </button>
      </div>
    </details>
  )
}
