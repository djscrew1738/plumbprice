// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement, type ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { EstimatesListPage } from './EstimatesListPage'

const { pushMock, getMock, deleteMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  getMock: vi.fn(),
  deleteMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/lib/api', () => ({
  api: {
    get: getMock,
    delete: deleteMock,
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
  },
  estimatesApi: {
    list: vi.fn(async () => {
      const res = await getMock('/estimates', { params: {} })
      const raw = res.data
      return { data: Array.isArray(raw) ? raw : (raw?.estimates ?? []) }
    }),
  },
}))

vi.mock('@/lib/outbox', () => ({
  enqueue: vi.fn(),
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

function renderWithQuery(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(createElement(QueryClientProvider, { client: qc }, ui))
}

describe('EstimatesListPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    getMock.mockReset()
    deleteMock.mockReset()
  })

  it('shows empty state with Start Estimating action when no estimates exist', async () => {
    getMock.mockResolvedValue({ data: [] })
    const user = userEvent.setup()

    renderWithQuery(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())
    expect(await screen.findByText(/no estimates yet/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start estimating/i }))
    expect(pushMock).toHaveBeenCalledWith('/estimator')
  })

  it('normalizes { estimates: [] } envelope from API without crashing', async () => {
    getMock.mockResolvedValue({ data: { estimates: [] } })

    renderWithQuery(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())
    expect(await screen.findByText(/no estimates yet/i)).toBeInTheDocument()
  })

  it('renders estimate rows when data is returned', async () => {
    getMock.mockResolvedValue({
      data: [
        {
          id: 1,
          title: 'Toilet replacement',
          job_type: 'service',
          status: 'draft',
          grand_total: 450,
          confidence_label: 'HIGH',
          county: 'Dallas',
          created_at: '2026-04-01T12:00:00Z',
        },
      ],
    })

    renderWithQuery(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())
    const matches = await screen.findAllByText('Toilet replacement')
    expect(matches.length).toBeGreaterThan(0)
  })
})
