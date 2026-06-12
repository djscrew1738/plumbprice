import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Card } from './Card'

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Content</Card>)
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('renders with panel variant and large size', () => {
    const { container } = render(<Card variant="panel" size="lg" padding="lg">Panel</Card>)
    expect(container.firstChild).toHaveClass('rounded-[var(--radius-xl)]')
  })

  it('renders layout subcomponents', () => {
    render(
      <Card>
        <Card.Header separated>
          <Card.Title>Title</Card.Title>
          <Card.Description>Description</Card.Description>
        </Card.Header>
        <Card.Body>Body</Card.Body>
        <Card.Footer separated>Footer</Card.Footer>
        <Card.Media>Media</Card.Media>
        <Card.Actions>Actions</Card.Actions>
      </Card>
    )

    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Description')).toBeInTheDocument()
    expect(screen.getByText('Body')).toBeInTheDocument()
    expect(screen.getByText('Footer')).toBeInTheDocument()
    expect(screen.getByText('Media')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
  })

  it('supports interactive variant', () => {
    const { container } = render(<Card interactive>Clickable</Card>)
    expect(container.firstChild).toHaveClass('cursor-pointer')
  })

  it('supports tone variants', () => {
    const { container } = render(<Card tone="accent">Accent</Card>)
    expect(container.firstChild).toHaveClass('border-[color:var(--accent)]/30')
  })
})
