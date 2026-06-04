import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Home from './page'

const { cookiesMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
}))

vi.mock('next/headers', () => ({
  cookies: cookiesMock,
}))

vi.mock('@/components/workspace/LauncherHome', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/components/workspace/LauncherHome')>()
  return {
    ...actual,
    LauncherHome: () => <div>Launcher workspace</div>,
    LauncherHomeSkeleton: () => <div>Launcher skeleton</div>,
  }
})

vi.mock('@/components/workspace/PublicHome', () => ({
  PublicHome: () => <div>Public landing</div>,
}))

describe('Home route', () => {
  beforeEach(() => {
    cookiesMock.mockReset()
  })

  it('renders the public landing page when no session cookie is present', async () => {
    cookiesMock.mockResolvedValue({
      get: vi.fn().mockReturnValue(undefined),
    })

    const page = await Home()
    render(page)

    expect(screen.getByText('Public landing')).toBeInTheDocument()
    expect(screen.queryByText('Launcher workspace')).not.toBeInTheDocument()
  })

  it('renders the workspace shell when a session cookie is present', async () => {
    cookiesMock.mockResolvedValue({
      get: vi.fn().mockReturnValue({ value: 'session-cookie' }),
    })

    const page = await Home()
    render(page)

    expect(screen.getByText('Launcher workspace')).toBeInTheDocument()
    expect(screen.queryByText('Public landing')).not.toBeInTheDocument()
  })
})
