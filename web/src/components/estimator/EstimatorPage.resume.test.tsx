// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { createElement } from 'react'
import type { ComponentPropsWithoutRef } from 'react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { EstimatorPage } from './EstimatorPage'

const { estimateGetMock, chatPriceMock } = vi.hoisted(() => ({
  estimateGetMock: vi.fn(),
  chatPriceMock: vi.fn(),
}))

let currentSearch = 'estimateId=138'

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(currentSearch),
}))

vi.mock('next/link', () => ({
  default: ({ children, href, ...props }: ComponentPropsWithoutRef<'a'>) =>
    createElement('a', { href, ...props }, children),
}))

vi.mock('@/lib/api', () => ({
  chatApi: {
    price: chatPriceMock,
  },
  estimatesApi: {
    get: estimateGetMock,
  },
  templatesApi: {
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

vi.mock('@/components/ui/Toast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  }),
}))

describe('EstimatorPage resume behavior', () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn()
    estimateGetMock.mockReset()
    chatPriceMock.mockReset()
    currentSearch = 'estimateId=138'
  })

  afterEach(() => {
    cleanup()
  })

  it('loads and surfaces a saved estimate when estimateId is present', async () => {
    estimateGetMock.mockResolvedValue({
      data: {
        id: 138,
        title: 'Master Bath — Toilet Replacement',
        status: 'draft',
        county: 'Dallas',
        confidence_score: 0.92,
        confidence_label: 'HIGH',
        assumptions: ['Standard first-floor access'],
        labor_total: 450,
        materials_total: 650,
        tax_total: 85,
        markup_total: 45,
        misc_total: 20,
        subtotal: 1165,
        grand_total: 1250,
        line_items: [
          {
            line_type: 'labor',
            description: 'Toilet replacement labor',
            quantity: 1,
            unit: 'ea',
            unit_cost: 450,
            total_cost: 450,
          },
        ],
      },
    })

    render(createElement(EstimatorPage))

    await waitFor(() => expect(estimateGetMock).toHaveBeenCalledWith(138))
    expect(await screen.findByText(/loaded estimate #138/i)).toBeInTheDocument()
  })

  it('reloads resumed state when estimateId query param changes', async () => {
    estimateGetMock.mockImplementation(async (id: number) => {
      if (id === 138) {
        return {
          data: {
            id: 138,
            title: 'First loaded estimate',
            status: 'draft',
            county: 'Dallas',
            confidence_score: 0.91,
            confidence_label: 'HIGH',
            assumptions: [],
            labor_total: 300,
            materials_total: 400,
            tax_total: 58,
            markup_total: 22,
            misc_total: 20,
            subtotal: 800,
            grand_total: 800,
            line_items: [],
          },
        }
      }

      return {
        data: {
          id: 222,
          title: 'Second loaded estimate',
          status: 'sent',
          county: 'Tarrant',
          confidence_score: 0.88,
          confidence_label: 'MEDIUM',
          assumptions: [],
          labor_total: 500,
          materials_total: 700,
          tax_total: 103,
          markup_total: 47,
          misc_total: 30,
          subtotal: 1380,
          grand_total: 1380,
          line_items: [],
        },
      }
    })

    const { rerender } = render(createElement(EstimatorPage))

    await waitFor(() => expect(estimateGetMock).toHaveBeenCalledWith(138))
    expect(await screen.findByText(/loaded estimate #138/i)).toBeInTheDocument()

    currentSearch = 'estimateId=222'
    rerender(createElement(EstimatorPage))

    await waitFor(() => expect(estimateGetMock).toHaveBeenCalledWith(222))
    expect(await screen.findByText(/loaded estimate #222/i)).toBeInTheDocument()
  })

  it('does not refetch the same estimate on an equivalent rerender', async () => {
    estimateGetMock.mockResolvedValue({
      data: {
        id: 138,
        title: 'Stable estimate',
        status: 'draft',
        county: 'Dallas',
        confidence_score: 0.9,
        confidence_label: 'HIGH',
        assumptions: [],
        labor_total: 200,
        materials_total: 300,
        tax_total: 41,
        markup_total: 19,
        misc_total: 10,
        subtotal: 570,
        grand_total: 570,
        line_items: [],
      },
    })

    const { rerender } = render(createElement(EstimatorPage))

    await waitFor(() => expect(estimateGetMock).toHaveBeenCalled())
    const callCountAfterInitialLoad = estimateGetMock.mock.calls.length

    rerender(createElement(EstimatorPage))

    await waitFor(() => {
      expect(estimateGetMock.mock.calls.length).toBe(callCountAfterInitialLoad)
    })
  })
})
