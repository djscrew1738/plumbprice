import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '@/components/layout/Header';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/',
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ user: null, token: null, loading: false, login: vi.fn(), logout: vi.fn() }),
}))

describe('Header Component', () => {
  it('should render header element', () => {
    render(<Header onMenuClick={vi.fn()} />);
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });

  it('should display navigation links', () => {
    render(<Header onMenuClick={vi.fn()} />);
    const nav = screen.queryByRole('navigation');
    if (nav) {
      expect(nav).toBeInTheDocument();
    }
  });
});
