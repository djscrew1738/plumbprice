import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { FormLayout } from './FormLayout'

describe('FormLayout', () => {
  it('renders title, description, and submit button', () => {
    render(
      <FormLayout title="Sign in" description="Enter your details" submitLabel="Continue">
        <input name="email" />
      </FormLayout>
    )

    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByText('Enter your details')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue' })).toBeInTheDocument()
  })

  it('calls onSubmit when the form is submitted', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn(e => e.preventDefault())

    render(
      <FormLayout onSubmit={onSubmit} submitLabel="Save">
        <input name="name" />
      </FormLayout>
    )

    await user.click(screen.getByRole('button', { name: 'Save' }))
    expect(onSubmit).toHaveBeenCalled()
  })

  it('displays an error and disables the submit button while submitting', () => {
    render(
      <FormLayout error="Invalid credentials" isSubmitting submitLabel="Sign in">
        <input name="email" />
      </FormLayout>
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials')
    expect(screen.getByRole('button', { name: 'Please wait…' })).toBeDisabled()
  })

  it('renders secondary action and footer', () => {
    render(
      <FormLayout submitLabel="Submit" secondaryAction={<a href="/help">Help</a>} footer={<span>Footer text</span>}>
        <input name="x" />
      </FormLayout>
    )

    expect(screen.getByRole('link', { name: 'Help' })).toBeInTheDocument()
    expect(screen.getByText('Footer text')).toBeInTheDocument()
  })
})
