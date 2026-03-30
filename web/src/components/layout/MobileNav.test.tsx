// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MobileNav } from './MobileNav'

vi.mock('next/navigation', () => ({
  usePathname: () => '/',
}))

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: ComponentPropsWithoutRef<'a'>) =>
    createElement('a', { href, ...props }, children),
}))

describe('MobileNav', () => {
  it('shows the field-first tabs and opens More for utility destinations', async () => {
    const onOpenMore = vi.fn()
    const user = userEvent.setup()

    render(createElement(MobileNav, { onOpenMore }))

    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /jobs/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /pipeline/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /more/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /suppliers/i })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /more/i }))

    expect(onOpenMore).toHaveBeenCalledTimes(1)
  })
})
