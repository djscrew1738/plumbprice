import Link from 'next/link'
import { Droplets } from 'lucide-react'
import { BrandFooter } from '@/components/layout/BrandFooter'

export default function NotFound() {
  return (
    <div className="min-h-dvh bg-[color:var(--canvas)] flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, hsl(var(--accent-hsl) / 0.10) 0%, transparent 70%)' }}
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
          <p className="text-8xl font-black text-[color:var(--line)] mb-2 select-none">404</p>
          <h2 className="text-xl font-bold text-[color:var(--ink)] mb-2">Page not found</h2>
          <p className="text-sm text-[color:var(--muted-ink)] mb-6">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-xl bg-gradient-to-br from-[color:var(--accent)] to-[color:var(--accent-strong)] px-5 py-2.5 text-sm font-semibold text-[color:var(--ink-inverse)] shadow-[0_4px_12px_var(--accent-glow)] hover:brightness-110 transition-all"
          >
            Back to Home
          </Link>
        </div>

        <BrandFooter className="mt-5" />
      </div>
    </div>
  )
}
