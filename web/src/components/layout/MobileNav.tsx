'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { MessageSquare, FileText, Package, Settings } from 'lucide-react'

const tabs = [
  { href: '/estimator', icon: MessageSquare, label: 'Estimator' },
  { href: '/estimates', icon: FileText, label: 'Estimates' },
  { href: '/suppliers', icon: Package, label: 'Suppliers' },
  { href: '/admin', icon: Settings, label: 'Admin' },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 inset-x-0 bg-black/70 backdrop-blur-2xl border-t border-white/5 z-40 lg:hidden"
      style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 8px)' }}>
      <div className="flex">
        {tabs.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={`relative flex-1 flex flex-col items-center justify-center py-2 gap-0.5 transition-colors duration-150 min-h-[56px] ${
                active ? 'text-blue-400' : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              <div className="relative">
                <Icon size={22} strokeWidth={active ? 2.5 : 1.75} />
                {active && (
                  <div className="absolute -inset-1.5 bg-blue-500/20 rounded-xl blur-sm" />
                )}
              </div>
              <span className={`text-[10px] font-semibold tracking-wide ${active ? 'text-blue-400' : 'text-zinc-500'}`}>
                {label}
              </span>
              {active && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-1.5 w-4 h-[2px] bg-blue-500 rounded-full"
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                />
              )}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
