import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'

const TestComponent = () => {
  const { user, logout } = useAuth()
  return (
    <div>
      <div data-testid="auth-status">
        {user ? `Logged in as ${user.email}` : 'Not logged in'}
      </div>
      <button onClick={logout} data-testid="logout-btn">Logout</button>
    </div>
  )
}

describe('AuthContext', () => {
  it('provides auth context with default values', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    expect(screen.getByTestId('auth-status').textContent).toBe('Not logged in')
  })

  it('renders logout button', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    expect(screen.getByTestId('logout-btn')).toBeInTheDocument()
  })

  it('handles logout action without throwing', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    expect(() => screen.getByTestId('logout-btn').click()).not.toThrow()
  })
})
