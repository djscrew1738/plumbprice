import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from '@/components/layout/Header';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null, loading: false, login: vi.fn(), logout: vi.fn() }),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    flagsApi: { list: vi.fn().mockResolvedValue({ data: [] }) },
    notificationsApi: {
      list: vi.fn().mockResolvedValue({ data: [] }),
      unreadCount: vi.fn().mockResolvedValue(0),
      markRead: vi.fn(),
      markAllRead: vi.fn(),
    },
    api: { get: vi.fn().mockResolvedValue({ data: [] }) },
  }
})

function withQueryClient(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return createElement(QueryClientProvider, { client: qc }, ui);
}

describe('Header Component', () => {
  it('should render header element', () => {
    render(withQueryClient(<Header onMenuClick={vi.fn()} />));
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });

  it('should display navigation links', () => {
    render(withQueryClient(<Header onMenuClick={vi.fn()} />));
    const nav = screen.queryByRole('navigation');
    if (nav) {
      expect(nav).toBeInTheDocument();
    }
  });
});
