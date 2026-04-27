'use client'

import { useCallback, useEffect, useState, type ReactNode } from 'react'
import dynamic from 'next/dynamic'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { usePathname } from 'next/navigation'
import { AnimatePresence, motion } from 'framer-motion'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { MobileNav } from '@/components/layout/MobileNav'
import { ToastProvider } from '@/components/ui/Toast'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'
import { ErrorFallback } from '@/components/ui/ErrorBoundary'
import { AuthProvider } from '@/contexts/AuthContext'
import { RouteAnnouncer } from '@/components/layout/RouteAnnouncer'
import { OfflineBanner } from '@/components/layout/OfflineBanner'
import { UpdateBanner } from '@/components/layout/UpdateBanner'

// Lazy-load dialogs/banners that are off-screen until activated by a
// keyboard shortcut or first-paint logic — keeps them out of the initial
// JS bundle for faster Time-to-Interactive.
const ShortcutsDialog = dynamic(
  () => import('@/components/ui/ShortcutsDialog').then(m => ({ default: m.ShortcutsDialog })),
  { ssr: false }
)
const CommandPalette = dynamic(
  () => import('@/components/ui/CommandPalette').then(m => ({ default: m.CommandPalette })),
  { ssr: false }
)
const MoreSheet = dynamic(
  () => import('@/components/layout/MoreSheet').then(m => ({ default: m.MoreSheet })),
  { ssr: false }
)
const WhatsNewBanner = dynamic(
  () => import('@/components/ui/WhatsNewBanner').then(m => ({ default: m.WhatsNewBanner })),
  { ssr: false }
)
import { InstallPrompt } from '@/components/layout/InstallPrompt'
import { useKeyboardShortcuts } from '@/lib/useKeyboardShortcuts'
import { registerServiceWorker } from '@/lib/registerSW'

export function ClientLayout({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60_000,   // 5 min — reduces refetches on route transitions
        gcTime: 10 * 60_000,     // 10 min — must exceed staleTime to avoid early GC
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  }))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)
  const pathname = usePathname()

  useKeyboardShortcuts()

  useEffect(() => {
    setSidebarOpen(false)
    setMoreOpen(false)
  }, [pathname])

  useEffect(() => {
    registerServiceWorker()
  }, [])

  const openMoreSheet = useCallback(() => setMoreOpen(true), [])
  const closeMoreSheet = useCallback(() => setMoreOpen(false), [])
  const openSidebar = useCallback(() => setSidebarOpen(true), [])
  const closeSidebar = useCallback(() => setSidebarOpen(false), [])

  const handleSkipToMain = (e: React.MouseEvent) => {
    e.preventDefault()
    const main = document.getElementById('main-content')
    main?.focus()
  }

  // Public, unauthenticated surfaces (customer proposal viewer) render without
  // the app chrome — no sidebar, header, mobile nav, or auth provider.
  const isPublicSurface = pathname?.startsWith('/p/') ?? false

  // Auth pages need AuthProvider (for useAuth()) but not app chrome —
  // they render their own full-screen layout.
  const isAuthPage = ['/login', '/register', '/forgot-password'].includes(pathname ?? '')

  return (
    <>
      <OfflineBanner />
      <UpdateBanner />
      {!isPublicSurface && <InstallPrompt />}
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
        <QueryClientProvider client={queryClient}>
        {isPublicSurface ? (
          <ToastProvider>
            <main id="main-content" tabIndex={-1} className="min-h-dvh outline-none">
              {children}
            </main>
          </ToastProvider>
        ) : isAuthPage ? (
          <AuthProvider>
          <ToastProvider>
            <main id="main-content" tabIndex={-1} className="min-h-dvh outline-none">
              {children}
            </main>
          </ToastProvider>
          </AuthProvider>
        ) : (
        <AuthProvider>
        <ToastProvider>
          <div className="flex min-h-dvh">
            <Sidebar open={sidebarOpen} onClose={closeSidebar} />

            {/* Mobile overlay */}
            <AnimatePresence>
              {sidebarOpen && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.18 }}
                  className="fixed inset-0 bg-black/70 backdrop-blur-sm z-30 lg:hidden"
                  onClick={closeSidebar}
                  aria-hidden={sidebarOpen ? "false" : "true"}
                />
              )}
            </AnimatePresence>

            {/* Main */}
            <div id="main-content" tabIndex={-1} className="flex-1 flex flex-col min-h-0 min-w-0 lg:ml-[248px] outline-none">
              <Header onMenuClick={openSidebar} />
              <main className="app-scroll flex-1 overflow-y-auto overflow-x-hidden">
                <AnimatePresence initial={false}>
                  <motion.div
                    key={pathname}
                    initial={{ opacity: 0, y: 2 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.12, ease: 'easeOut' }}
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
                <div className="h-[calc(var(--mobile-nav-height)+env(safe-area-inset-bottom))] lg:hidden" aria-hidden="true" />
              </main>
            </div>

            <MobileNav onOpenMore={openMoreSheet} />
            <MoreSheet open={moreOpen} onClose={closeMoreSheet} />
          </div>
        </ToastProvider>
        <ShortcutsDialog />
        <CommandPalette />
        {!isPublicSurface && <WhatsNewBanner />}
        <RouteAnnouncer />
        </AuthProvider>
        )}
        </QueryClientProvider>
      </ErrorBoundary>
    </>
  )
}
