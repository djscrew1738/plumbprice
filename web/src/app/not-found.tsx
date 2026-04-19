import Link from 'next/link'
import { Droplets } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, hsl(160 60% 45% / 0.12) 0%, transparent 70%)' }}
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
          <p className="text-8xl font-black text-white/10 mb-2 select-none">404</p>
          <h2 className="text-xl font-bold text-white mb-2">Page not found</h2>
          <p className="text-sm text-zinc-500 mb-6">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-colors"
          >
            Back to Home
          </Link>
        </div>

        <p className="text-center text-[11px] text-zinc-700 mt-5">
          PlumbPrice AI · DFW Contractors Only
        </p>
      </div>
    </div>
  )
}
