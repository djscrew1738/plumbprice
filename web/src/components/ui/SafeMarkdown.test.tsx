import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SafeMarkdown } from './SafeMarkdown'

describe('SafeMarkdown', () => {
  it('renders markdown text', () => {
    render(<SafeMarkdown>Hello **world**</SafeMarkdown>)
    expect(screen.getByText('world')).toBeInTheDocument()
  })

  it('adds rel and target to external links', () => {
    render(<SafeMarkdown>[link](https://example.com)</SafeMarkdown>)
    const link = screen.getByRole('link', { name: 'link' })
    expect(link).toHaveAttribute('href', 'https://example.com')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer nofollow')
  })

  it('does not add target/rel to relative links', () => {
    render(<SafeMarkdown>[link](/estimates)</SafeMarkdown>)
    const link = screen.getByRole('link', { name: 'link' })
    expect(link).toHaveAttribute('href', '/estimates')
    expect(link).not.toHaveAttribute('target')
    expect(link).not.toHaveAttribute('rel')
  })

  it('strips dangerous link protocols', () => {
    render(<SafeMarkdown>[bad](javascript:alert(1))</SafeMarkdown>)
    // react-markdown urlTransform strips the href — link may render without href
    const link = screen.queryByRole('link', { name: 'bad' })
    if (link) {
      expect(link).not.toHaveAttribute('href', 'javascript:alert(1)')
    } else {
      // href stripped entirely — text still rendered
      expect(screen.getByText('bad')).toBeInTheDocument()
    }
  })

  it('renders markdown lists', () => {
    const markdown = `- one
- two`
    render(<SafeMarkdown>{markdown}</SafeMarkdown>)
    expect(screen.getByText('one')).toBeInTheDocument()
    expect(screen.getByText('two')).toBeInTheDocument()
  })
})
