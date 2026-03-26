'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, FileText, Package, Layers, FileOutput, Settings, X, Droplets } from 'lucide-react'

const navItems = [
  { href: '/estimator', icon: MessageSquare, label: 'Chat Estimator' },
  { href: '/estimates', icon: FileText, label: 'Estimates' },
  { href: '/suppliers', icon: Package, label: 'Suppliers' },
  { href: '/blueprints', icon: Layers, badge: 'Phase 4', label: 'Blueprints' },
  { href: '/proposals', icon: FileOutput, badge: 'Phase 2', label: 'Proposals' },
  { href: '/admin', icon: Settings, label: 'Admin' },
]

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname()

  const sidebarContent = (
    <>
      {/* Glow accent line */}
      <div className="h-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent" />

      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Droplets size={18} className="text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-sm leading-none tracking-tight">PlumbPrice</div>
            <div className="text-blue-400 text-[10px] font-medium leading-none mt-0.5">DFW AI Estimator</div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {navItems.map(({ href, icon: Icon, label, badge }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150 group ${
                active
                  ? 'bg-white/10 text-white'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              {active && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-blue-500 rounded-r-full" />
              )}
              <Icon size={18} strokeWidth={active ? 2.5 : 1.75} className="shrink-0" />
              <span className="text-sm font-medium">{label}</span>
              {badge && (
                <span className="ml-auto text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-white/5 text-zinc-500 border border-white/[0.06] leading-none">
                  {badge}
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-white/[0.06]">
        <div className="text-[11px] text-zinc-600">
          <div className="font-semibold text-zinc-500">PlumbPrice AI v0.1.0</div>
          <div className="mt-0.5">DFW Market Pricing</div>
        </div>
      </div>
    </>
  )

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden lg:flex fixed inset-y-0 left-0 w-64 bg-black/40 backdrop-blur-2xl border-r border-white/[0.06] z-40 flex-col"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        {sidebarContent}
      </aside>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {open && (
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-y-0 left-0 w-64 bg-[#0a0a0a]/95 backdrop-blur-2xl border-r border-white/[0.06] z-40 flex flex-col lg:hidden"
            style={{ paddingTop: 'env(safe-area-inset-top)' }}
          >
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}
