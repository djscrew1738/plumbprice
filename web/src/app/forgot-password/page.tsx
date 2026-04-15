'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { Droplets, Mail, ArrowLeft } from 'lucide-react'

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-dvh bg-[#060606] flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[120px]"
          style={{ background: 'radial-gradient(circle, hsl(var(--accent-hsl) / 0.12) 0%, transparent 70%)' }}
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="w-full max-w-sm"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-700 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-600/30 mb-4">
            <Droplets size={26} className="text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">PlumbPrice AI</h1>
          <p className="text-sm text-zinc-600 mt-1">Password Reset</p>
        </div>

        {/* Card */}
        <div className="bg-[#0f0f0f] border border-white/[0.08] rounded-2xl p-6 shadow-2xl text-center space-y-4">
          <div className="flex justify-center">
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center">
              <Mail size={22} className="text-blue-400" />
            </div>
          </div>

          <div>
            <h2 className="text-base font-bold text-[color:var(--ink)] mb-1">
              Password reset via admin
            </h2>
            <p className="text-sm text-[color:var(--muted-ink)] leading-relaxed">
              PlumbPrice AI is invite-only. To reset your password, contact your
              account administrator or email{' '}
              <a
                href="mailto:support@ctlplumbingllc.com"
                className="text-[color:var(--accent)] hover:underline"
              >
                support@ctlplumbingllc.com
              </a>
              .
            </p>
          </div>

          <div className="pt-2">
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-sm text-[color:var(--muted-ink)] hover:text-[color:var(--ink)] transition-colors"
            >
              <ArrowLeft size={14} />
              Back to sign in
            </Link>
          </div>
        </div>

        <p className="text-center text-[11px] text-zinc-700 mt-5">
          PlumbPrice AI · DFW Contractors Only
        </p>
      </motion.div>
    </div>
  )
}
