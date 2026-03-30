// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import type { ChatMessage } from '@/types'
import { describe, expect, it, vi } from 'vitest'
import { WorkspaceSummaryRail } from './WorkspaceSummaryRail'

const { estimateBreakdownMock } = vi.hoisted(() => ({
  estimateBreakdownMock: vi.fn(),
}))

vi.mock('../estimator/EstimateBreakdown', () => ({
  EstimateBreakdown: (props: unknown) => {
    estimateBreakdownMock(props)
    return <div data-testid="estimate-breakdown" />
  },
}))

function createSelectedEstimate(): ChatMessage {
  return {
    id: 'assistant-1',
    role: 'assistant',
    content: 'Here is your estimate.',
    estimate: {
      labor_total: 450,
      materials_total: 650,
      tax_total: 85,
      markup_total: 45,
      misc_total: 20,
      subtotal: 1250,
      grand_total: 1250,
      line_items: [],
    },
    confidence: 0.91,
    confidence_label: 'HIGH',
    assumptions: ['Standard first-floor access'],
    timestamp: new Date('2026-03-30T00:00:00.000Z'),
  }
}

describe('WorkspaceSummaryRail', () => {
  it('shows an empty desktop rail when no estimate is selected', () => {
    render(
      <WorkspaceSummaryRail
        county="Dallas"
        selectedEstimate={null}
        sheetOpen={false}
        onSheetOpenChange={() => {}}
      />
    )

    expect(screen.getByText(/estimate summary/i)).toBeInTheDocument()
    expect(screen.getByText(/ask a pricing question to populate totals/i)).toBeInTheDocument()
    expect(screen.queryByTestId('estimate-breakdown')).not.toBeInTheDocument()
  })

  it('renders the estimate breakdown and mobile total affordance', () => {
    const onSheetOpenChange = vi.fn()

    render(
      <WorkspaceSummaryRail
        county="Dallas"
        selectedEstimate={createSelectedEstimate()}
        sheetOpen={false}
        onSheetOpenChange={onSheetOpenChange}
      />
    )

    expect(screen.getByTestId('estimate-breakdown')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /view total \$1,250/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /view total \$1,250/i }))
    expect(onSheetOpenChange).toHaveBeenCalledWith(true)
    expect(estimateBreakdownMock).toHaveBeenCalledWith(
      expect.objectContaining({
        county: 'Dallas',
        confidenceLabel: 'HIGH',
        confidenceScore: 0.91,
        assumptions: ['Standard first-floor access'],
      })
    )
  })

  it('shows and closes the mobile bottom sheet when opened', () => {
    const onSheetOpenChange = vi.fn()

    render(
      <WorkspaceSummaryRail
        county="Dallas"
        selectedEstimate={createSelectedEstimate()}
        sheetOpen
        onSheetOpenChange={onSheetOpenChange}
      />
    )

    expect(screen.getByRole('dialog', { name: /estimate summary sheet/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /close summary/i }))
    expect(onSheetOpenChange).toHaveBeenCalledWith(false)
  })
})
