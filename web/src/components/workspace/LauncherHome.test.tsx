// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LauncherHome } from './LauncherHome'

const { listMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
}))

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: ComponentPropsWithoutRef<'a'>) =>
    createElement('a', { href, ...props }, children),
}))

vi.mock('@/lib/api', () => ({
  estimatesApi: {
    list: listMock,
  },
}))

describe('LauncherHome', () => {
  beforeEach(() => {
    listMock.mockReset()
  })

  it('shows launcher actions and maps recent job statuses to user-facing labels', async () => {
    listMock.mockResolvedValue({
      data: [
        {
          id: 321,
          title: 'Main line cleanout',
          job_type: 'service',
          status: 'draft',
          grand_total: 425,
          confidence_label: 'MEDIUM',
          county: 'Dallas',
          created_at: '2026-03-28T14:15:00.000Z',
        },
        {
          id: 322,
          title: 'Water heater replacement',
          job_type: 'service',
          status: 'accepted',
          grand_total: 1850,
          confidence_label: 'HIGH',
          county: 'Tarrant',
          created_at: '2026-03-28T12:45:00.000Z',
        },
      ],
    })

    render(createElement(LauncherHome))

    expect(screen.getByText(/field pricing launcher/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /quick quote/i })).toHaveAttribute(
      'href',
      '/estimator?entry=quick-quote'
    )
    expect(screen.getByRole('link', { name: /upload job files/i })).toHaveAttribute(
      'href',
      '/estimator?entry=upload-job-files'
    )

    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect(await screen.findByText('Main line cleanout')).toBeInTheDocument()
    expect(screen.getByText('Awaiting details')).toBeInTheDocument()
    expect(screen.getByText('Estimate ready')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /main line cleanout/i })).toHaveAttribute(
      'href',
      '/estimator?estimateId=321'
    )
    expect(screen.getByRole('link', { name: /water heater replacement/i })).toHaveAttribute(
      'href',
      '/estimator?estimateId=322'
    )
  })
})
