import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { api } from '@/lib/api'

// Mock the api module
vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const TestComponent = () => {
  const { user, logout, loading } = useAuth()
  if (loading) return <div>Loading...</div>
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
  beforeEach(() => {
    vi.clearAllMocks()
    // Default mock response for hydration
    ;(api.get as any).mockResolvedValue({ data: null })
  })

  it('provides auth context with default values after loading', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    
    // Initially shows loading
    expect(screen.getByText('Loading...')).toBeInTheDocument()

    // Wait for hydration to finish
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })
    
    await waitFor(() => {
      expect(screen.getByTestId('auth-status').textContent).toBe('Not logged in')
    })
  })

  it('renders logout button', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    await waitFor(() => {
      expect(screen.getByTestId('logout-btn')).toBeInTheDocument()
    })
  })

  it('handles logout action without throwing', async () => {
    (api.post as any).mockResolvedValue({ data: {} })
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    )
    
    await waitFor(() => {
      const btn = screen.getByTestId('logout-btn')
      btn.click()
    })
    
    expect(api.post).toHaveBeenCalledWith('/auth/logout')
  })
})
