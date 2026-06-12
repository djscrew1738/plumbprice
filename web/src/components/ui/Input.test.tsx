import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Mail, Search } from 'lucide-react'
import { Input } from './Input'

describe('Input', () => {
  it('renders an accessible labelled input', () => {
    render(<Input label="Email" placeholder="you@example.com" />)

    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument()
  })

  it('displays an error message and sets aria-invalid', () => {
    render(<Input label="Password" error="Required" />)

    const input = screen.getByLabelText('Password')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert')).toHaveTextContent('Required')
  })

  it('shows helper text when no error is present', () => {
    render(<Input label="Username" helperText="Pick something unique" />)

    expect(screen.getByText('Pick something unique')).toBeInTheDocument()
  })

  it('renders left and right icons', () => {
    const { container } = render(
      <Input label="Search" leftIcon={<Search data-testid="left" />} rightIcon={<Mail data-testid="right" />} />
    )

    expect(container.querySelector('[data-testid="left"]')).toBeInTheDocument()
    expect(container.querySelector('[data-testid="right"]')).toBeInTheDocument()
  })

  it('renders an interactive right action', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    render(
      <Input
        label="Password"
        rightAction={<button type="button" onClick={onClick}>Toggle</button>}
      />
    )

    const button = screen.getByRole('button', { name: 'Toggle' })
    expect(button).toBeInTheDocument()
    await user.click(button)
    expect(onClick).toHaveBeenCalled()
  })

  it('forwards refs', () => {
    let received: HTMLInputElement | null = null
    render(<Input label="Ref" ref={el => { received = el }} />)

    expect(received).toBeInstanceOf(HTMLInputElement)
  })
})
