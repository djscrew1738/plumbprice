import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { LoginForm } from './LoginForm'

const login = vi.fn()
const loginAsGuest = vi.fn()
const replace = vi.fn()
const getParam = vi.fn()

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ login, loginAsGuest }),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => ({ get: getParam }),
}))

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getParam.mockReturnValue(null)
  })

  it('signs in with email and password', async () => {
    const user = userEvent.setup()
    login.mockResolvedValueOnce(undefined)

    render(<LoginForm />)

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(login).toHaveBeenCalledWith('test@example.com', 'password123'))
    expect(replace).toHaveBeenCalledWith('/')
  })

  it('shows an error when login fails', async () => {
    const user = userEvent.setup()
    login.mockRejectedValueOnce({ response: { data: { detail: 'Invalid credentials' } } })

    render(<LoginForm />)

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid credentials')
  })

  it('toggles password visibility', async () => {
    const user = userEvent.setup()
    render(<LoginForm />)

    const password = screen.getByLabelText('Password')
    expect(password).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Show password' }))
    expect(password).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(password).toHaveAttribute('type', 'password')
  })

  it('logs in as guest', async () => {
    const user = userEvent.setup()
    loginAsGuest.mockResolvedValueOnce(undefined)

    render(<LoginForm />)

    await user.click(screen.getByRole('button', { name: 'Continue as Guest' }))

    await waitFor(() => expect(loginAsGuest).toHaveBeenCalled())
    expect(replace).toHaveBeenCalledWith('/')
  })

  it('redirects to the value of the redirect query param', async () => {
    const user = userEvent.setup()
    getParam.mockReturnValue('/dashboard')
    login.mockResolvedValueOnce(undefined)

    render(<LoginForm />)

    await user.type(screen.getByLabelText('Email'), 'test@example.com')
    await user.type(screen.getByLabelText('Password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(replace).toHaveBeenCalledWith('/dashboard'))
  })
})
