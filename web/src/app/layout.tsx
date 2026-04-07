'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { MobileNav } from '@/components/layout/MobileNav'
import { MoreSheet } from '@/components/layout/MoreSheet'
import { ToastProvider } from '@/components/ui/Toast'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { ErrorFallback } from '@/components/ui/ErrorBoundary'
import { AuthProvider } from '@/contexts/AuthContext'
import './globals.css'

export default function RootLayout({ children }: { children: ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    setSidebarOpen(false)
    setMoreOpen(false)
  }, [pathname])

  const handleSkipToMain = () => {
    router.push(pathname, { scroll: false })
    const main = document.querySelector('main')
    main?.focus()
  }

  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        <meta name="theme-color" content="#f2ebe1" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="description" content="AI-powered plumbing estimator for DFW contractors" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/manifest.json" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <title>PlumbPrice AI</title>
      </head>
      <body className="bg-[hsl(var(--background))] text-[color:var(--ink)] antialiased">
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
                  <div className="h-20 lg:hidden" />
                </main>
              </div>

              <MobileNav onOpenMore={() => setMoreOpen(true)} />
              <MoreSheet open={moreOpen} onClose={() => setMoreOpen(false)} />
            </div>
          </ToastProvider>
          </AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  )
}
