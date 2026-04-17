// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PipelinePage } from './PipelinePage'

const { listMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useParams: () => ({}),
}))

vi.mock('@/lib/api', () => ({
  projectsApi: {
    list: listMock,
    update: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

const PIPELINE_DATA = {
  projects: [
    {
      id: 1,
      name: 'Main line replacement',
      job_type: 'service',
      status: 'lead',
      customer_name: 'John Smith',
      county: 'Dallas',
      city: 'Plano',
      estimate_count: 1,
      latest_estimate_total: 4200,
      created_at: '2026-03-20T10:00:00.000Z',
      updated_at: '2026-04-01T10:00:00.000Z',
    },
  ],
  summary: { lead: 1, estimate_sent: 0, won: 0, lost: 0 },
}

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    createElement(QueryClientProvider, { client: queryClient }, ui),
  )
}

describe('PipelinePage', () => {
  beforeEach(() => {
    listMock.mockReset()
    listMock.mockResolvedValue({ data: PIPELINE_DATA })
  })

  it('renders all four pipeline stage columns', async () => {
    renderWithProviders(createElement(PipelinePage))
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect((await screen.findAllByText('Lead')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Estimate Sent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Won').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lost').length).toBeGreaterThan(0)
  })

  it('shows a project card in the Lead stage', async () => {
    renderWithProviders(createElement(PipelinePage))
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect(await screen.findByText(/main line replacement/i)).toBeInTheDocument()
  })

  it('shows summary pipeline value', async () => {
    renderWithProviders(createElement(PipelinePage))
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect((await screen.findAllByText(/\$4,200/)).length).toBeGreaterThan(0)
  })

  it('shows error state when API fails', async () => {
    listMock.mockRejectedValue(new Error('Network error'))
    renderWithProviders(createElement(PipelinePage))
    expect(await screen.findByText(/could not load pipeline/i)).toBeInTheDocument()
  })

  it('shows empty state columns when all stages are empty', async () => {
    listMock.mockResolvedValue({
      data: {
        projects: [],
        summary: { lead: 0, estimate_sent: 0, won: 0, lost: 0 },
      },
    })
    renderWithProviders(createElement(PipelinePage))
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    expect(await screen.findByText(/no opportunities yet/i)).toBeInTheDocument()
  })
})
