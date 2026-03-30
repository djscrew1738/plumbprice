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
  useRouter: () => ({
    push: pushMock,
  }),
}))

vi.mock('@/lib/api', () => ({
  api: {
    get: getMock,
    delete: deleteMock,
  },
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

describe('EstimatesListPage', () => {
  beforeEach(() => {
    pushMock.mockReset()
    getMock.mockReset()
    deleteMock.mockReset()
    getMock.mockResolvedValue({ data: { estimates: [] } })
  })

  it('shows the saved estimates intro and routes Quick Quote into the estimator entry flow', async () => {
    const user = userEvent.setup()

    render(createElement(EstimatesListPage))

    await waitFor(() => expect(getMock).toHaveBeenCalled())

    expect(screen.getByRole('heading', { name: /review and resume saved estimates/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /quick quote/i }))

    expect(pushMock).toHaveBeenCalledWith('/estimator?entry=quick-quote')
  })
})
