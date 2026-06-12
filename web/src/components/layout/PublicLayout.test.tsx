import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PublicLayout } from './PublicLayout'

describe('PublicLayout', () => {
  it('renders title, subtitle, children, and footer', () => {
    render(
      <PublicLayout title="Sign in" subtitle="Welcome back" footer={<a href="/help">Need help?</a>}>
        <form aria-label="test-form">
          <input name="email" />
        </form>
      </PublicLayout>
    )

    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText('Welcome back')).toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'test-form' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Need help?' })).toBeInTheDocument()
  })

  it('supports compact mode', () => {
    const { container } = render(
      <PublicLayout title="Compact" compact>
        <div>content</div>
      </PublicLayout>
    )

    expect(container.querySelector('.mb-6')).toBeInTheDocument()
  })
})
