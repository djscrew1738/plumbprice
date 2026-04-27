// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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
  sessionsApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
  outcomesApi: {
    stats: vi.fn().mockResolvedValue({ data: { total: 0, won: 0, lost: 0, pending: 0, no_bid: 0, win_rate: null, confidence_breakdown: {} } }),
  },
}))

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const TestQueryClientProvider = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children)
  TestQueryClientProvider.displayName = 'TestQueryClientProvider'
  return TestQueryClientProvider
}

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

    render(createElement(LauncherHome), { wrapper: makeWrapper() })

    expect(screen.getByText(/estimator dashboard/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /quick quote/i })).toHaveAttribute(
      'href',
      '/estimator?entry=quick-quote',
    )
    expect(screen.getByRole('link', { name: /upload job files/i })).toHaveAttribute(
      'href',
      '/estimator?entry=upload-job-files',
    )

    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect(await screen.findByText('Main line cleanout')).toBeInTheDocument()
    expect(screen.getByText('Awaiting details')).toBeInTheDocument()
    expect(screen.getByText('Estimate ready')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /main line cleanout/i })).toHaveAttribute(
      'href',
      '/estimates/321',
    )
    expect(screen.getByRole('link', { name: /water heater replacement/i })).toHaveAttribute(
      'href',
      '/estimates/322',
    )
  })
})
