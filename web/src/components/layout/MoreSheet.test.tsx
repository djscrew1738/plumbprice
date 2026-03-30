// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MoreSheet } from './MoreSheet'

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: ComponentPropsWithoutRef<'a'>) =>
    createElement('a', { href, ...props }, children),
}))

describe('MoreSheet', () => {
  it('renders the utility destinations when opened', () => {
    render(<MoreSheet open onClose={() => {}} />)

    expect(screen.getByRole('link', { name: /suppliers/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /admin/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /blueprints/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /proposals/i })).toBeInTheDocument()
  })

  it('closes when the overlay is clicked or escape is pressed', () => {
    const onClose = vi.fn()

    render(<MoreSheet open onClose={onClose} />)

    // Click the most recently rendered overlay node.
    const overlays = screen.getAllByTestId('more-sheet-overlay')
    fireEvent.click(overlays[overlays.length - 1])
    expect(onClose).toHaveBeenCalledTimes(1)

    onClose.mockClear()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })
})
