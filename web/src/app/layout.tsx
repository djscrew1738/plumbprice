'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { MobileNav } from '@/components/layout/MobileNav'
import { MoreSheet } from '@/components/layout/MoreSheet'
import { ToastProvider } from '@/components/ui/Toast'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { ErrorFallback } from '@/components/ui/ErrorBoundary'
import { AuthProvider } from '@/contexts/AuthContext'
import { ShortcutsDialog } from '@/components/ui/ShortcutsDialog'
import { useKeyboardShortcuts } from '@/lib/useKeyboardShortcuts'
import './globals.css'

export default function RootLayout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const [isOffline, setIsOffline] = useState(false)
  const pathname = usePathname()

  useKeyboardShortcuts()

  useEffect(() => {
    setSidebarOpen(false)
    setMoreOpen(false)
  }, [pathname])

  useEffect(() => {
    setIsOffline(!navigator.onLine)
    const goOffline = () => setIsOffline(true)
    const goOnline = () => setIsOffline(false)
    window.addEventListener('offline', goOffline)
    window.addEventListener('online', goOnline)
    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('online', goOnline)
    }
  }, [])

  const handleSkipToMain = (e: React.MouseEvent) => {
    e.preventDefault()
    const main = document.getElementById('main-content')
    main?.focus()
  }

  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#1a1410" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="description" content="AI-powered plumbing estimator for DFW contractors" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <title>PlumbPrice AI</title>
      </head>
      <body className="bg-[hsl(var(--background))] text-[color:var(--ink)] antialiased">
        {isOffline && (
          <div className="offline-banner" role="alert">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="1" x2="23" y1="1" y2="23"/><path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"/><path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/><path d="M10.71 5.05A16 16 0 0 1 22.56 9"/><path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" x2="12.01" y1="20" y2="20"/></svg>
            You are offline — some features may be unavailable
          </div>
        )}
        {/* Skip to main content link for accessibility */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-[color:var(--accent)] focus:px-4 focus:py-2 focus:text-white"
          onClick={handleSkipToMain}
        >
          Skip to main content
        </a>

        <ErrorBoundary
          fallback={
            <ErrorFallback
              message="We're having trouble loading PlumbPrice AI. Please try refreshing."
              onRetry={() => window.location.reload()}
            />
          }
        >
          <AuthProvider>
          <ToastProvider>
            <div className="flex min-h-dvh">
              <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

              {/* Mobile overlay */}
              <AnimatePresence>
                {sidebarOpen && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18 }}
                    className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                    aria-hidden={sidebarOpen ? "false" : "true"}
                  />
                )}
              </AnimatePresence>

              {/* Main */}
              <div id="main-content" className="flex-1 flex flex-col min-w-0 lg:ml-[248px] outline-none">
                <Header onMenuClick={() => setSidebarOpen(true)} />
                <main className="flex-1 overflow-y-auto overflow-x-hidden">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={pathname}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.18, ease: 'easeOut' }}
                      className="h-full"
                    >
                      <ErrorBoundary
                        key={pathname}
                        fallback={
                          <ErrorFallback message="Failed to load this page. Please try again." onRetry={() => window.location.reload()} />
                        }
                      >
                        {children}
                      </ErrorBoundary>
                    </motion.div>
                  </AnimatePresence>
                  <div className="h-[var(--mobile-nav-height)] lg:hidden" />
                </main>
              </div>

              <MobileNav onOpenMore={() => setMoreOpen(true)} />
              <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
            </div>
          </ToastProvider>
          <ShortcutsDialog />
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
