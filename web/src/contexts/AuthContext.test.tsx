import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import AuthContext, { AuthProvider } from '@/contexts/AuthContext';
import { ReactNode } from 'react';

describe('AuthContext', () => {
  const TestComponent = () => {
    const { user, isAuthenticated, logout } = AuthContext.useContext() || {
      user: null,
      isAuthenticated: false,
      logout: vi.fn(),
    };

    return (
      <div>
        <div data-testid="auth-status">
          {isAuthenticated ? `Logged in as ${user?.email}` : 'Not logged in'}
        </div>
        <button onClick={logout} data-testid="logout-btn">
          Logout
        </button>
      </div>
    );
  };

  it('provides auth context with default values', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const status = screen.getByTestId('auth-status');
    expect(status.textContent).toBe('Not logged in');
  });

  it('renders logout button', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    const logoutBtn = screen.getByTestId('logout-btn');
    expect(logoutBtn).toBeInTheDocument();
  });

  it('handles logout action', () => {
    const TestLogout = () => {
      const context = AuthContext.useContext();
      if (!context) return null;

      return (
        <button onClick={context.logout} data-testid="logout">
          Logout
        </button>
      );
    };

    render(
      <AuthProvider>
        <TestLogout />
      </AuthProvider>
    );

    const btn = screen.getByTestId('logout');
    expect(btn).toBeInTheDocument();
  });
});
