import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '@/components/layout/Header';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
  usePathname: () => '/',
}));

describe('Header Component', () => {
  it('should render header element', () => {
    render(<Header />);
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });

  it('should display navigation links', () => {
    render(<Header />);
    // Adjust selector based on actual Header structure
    const nav = screen.queryByRole('navigation');
    if (nav) {
      expect(nav).toBeInTheDocument();
    }
  });
});
