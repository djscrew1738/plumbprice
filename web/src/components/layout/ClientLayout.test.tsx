import { render, screen } from '@testing-library/react'
import type { ComponentProps, ReactNode } from 'react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { ClientLayout } from './ClientLayout'

const { usePathnameMock, useAuthMock } = vi.hoisted(() => ({
  usePathnameMock: vi.fn(),
  useAuthMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  usePathname: usePathnameMock,
}))

vi.mock('next/dynamic', () => ({
  default: () => function MockDynamicComponent() {
    return null
  },
}))

vi.mock('framer-motion', () => ({
  AnimatePresence: ({ children }: { children: ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: ComponentProps<'div'>) => <div {...props}>{children}</div>,
    aside: ({ children, ...props }: ComponentProps<'aside'>) => <aside {...props}>{children}</aside>,
    span: ({ children, ...props }: ComponentProps<'span'>) => <span {...props}>{children}</span>,
  },
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: useAuthMock,
}))

vi.mock('@/components/layout/Sidebar', () => ({
  Sidebar: () => <aside aria-label="Main navigation">Sidebar</aside>,
}))

vi.mock('@/components/layout/Header', () => ({
  Header: () => <header>Header</header>,
}))

vi.mock('@/components/layout/MobileNav', () => ({
  MobileNav: () => <nav aria-label="Bottom navigation">Mobile nav</nav>,
}))

vi.mock('@/components/layout/MoreSheet', () => ({
  MoreSheet: () => null,
}))

vi.mock('@/components/layout/RouteAnnouncer', () => ({
  RouteAnnouncer: () => null,
}))

vi.mock('@/components/layout/OfflineBanner', () => ({
  OfflineBanner: () => <div>Offline banner</div>,
}))

vi.mock('@/components/layout/UpdateBanner', () => ({
  UpdateBanner: () => <div>Update banner</div>,
}))

vi.mock('@/components/layout/InstallPrompt', () => ({
  InstallPrompt: () => <div>Install prompt</div>,
}))

vi.mock('@/components/ui/WhatsNewBanner', () => ({
  WhatsNewBanner: () => <div>Whats new</div>,
}))

vi.mock('@/components/ui/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: ReactNode }) => <>{children}</>,
  ErrorFallback: () => null,
}))

vi.mock('@/lib/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: vi.fn(),
}))

vi.mock('@/lib/registerSW', () => ({
  registerServiceWorker: vi.fn(),
}))

vi.mock('@/lib/hooks', () => ({
  useSessionExpiry: vi.fn(),
}))

describe('ClientLayout', () => {
  beforeEach(() => {
    usePathnameMock.mockReturnValue('/')
    useAuthMock.mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
  })

  it('renders the homepage without app chrome when there is no session', () => {
    render(
      <ClientLayout initialHasSession={false}>
        <div>Public home content</div>
      </ClientLayout>,
    )

    expect(screen.getByText('Public home content')).toBeInTheDocument()
    expect(screen.queryByLabelText('Main navigation')).not.toBeInTheDocument()
    expect(screen.queryByText('Header')).not.toBeInTheDocument()
    expect(screen.queryByText('Offline banner')).not.toBeInTheDocument()
  })

  it('keeps the app chrome for authenticated home sessions', () => {
    useAuthMock.mockReturnValue({
      user: {
        id: 1,
        email: 'owner@example.com',
        full_name: 'Owner Operator',
        role: 'owner',
        is_admin: true,
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })

    render(
      <ClientLayout initialHasSession>
        <div>Workspace</div>
      </ClientLayout>,
    )

    expect(screen.getByLabelText('Main navigation')).toBeInTheDocument()
    expect(screen.getByText('Header')).toBeInTheDocument()
    expect(screen.getByText('Offline banner')).toBeInTheDocument()
  })
})
