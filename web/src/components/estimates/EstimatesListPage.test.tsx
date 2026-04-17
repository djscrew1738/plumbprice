// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EstimatesListPage } from './EstimatesListPage'

const { pushMock, getMock, deleteMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  getMock: vi.fn(),
  deleteMock: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    get: getMock,
    delete: deleteMock,
  },
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}))

describe('EstimatesListPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    getMock.mockReset()
    deleteMock.mockReset()
  })

  it('shows empty state with Start Estimating action when no estimates exist', async () => {
    getMock.mockResolvedValue({ data: [] })
    const user = userEvent.setup()

    render(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())
    expect(await screen.findByText(/no estimates yet/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start estimating/i }))
    expect(pushMock).toHaveBeenCalledWith('/estimator')
  })

  it('normalizes { estimates: [] } envelope from API without crashing', async () => {
    getMock.mockResolvedValue({ data: { estimates: [] } })

    render(createElement(EstimatesListPage))

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

    render(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())
    const matches = await screen.findAllByText('Toilet replacement')
    expect(matches.length).toBeGreaterThan(0)
  })
})
