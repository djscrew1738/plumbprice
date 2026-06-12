// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PublicQuotePage } from './PublicQuotePage'

const postMock = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api', () => ({
  api: {
    post: postMock,
  },
}))

describe('PublicQuotePage', () => {
  beforeEach(() => {
    postMock.mockReset()
  })

  it('renders the initial prompt and input form', () => {
    render(<PublicQuotePage />)
    expect(screen.getByText(/CTL Plumbing — Instant Quote/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Describe the job/i)).toBeInTheDocument()
  })

  it('shows clarification questions as clickable chips when status is clarification', async () => {
    postMock.mockResolvedValue({
      data: {
        status: 'clarification',
        answer: 'I need a little more detail.',
        clarification_questions: ['Is it a gas or electric heater?', 'What floor?'],
        follow_up_required: true,
      },
    })

    const user = userEvent.setup()
    render(<PublicQuotePage />)

    const input = screen.getByPlaceholderText(/Describe the job/i)
    await user.type(input, 'replace water heater')
    await user.click(screen.getByRole('button', { name: /Quote/i }))

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('I need a little more detail.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Is it a gas or electric heater?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'What floor?' })).toBeInTheDocument()
  })

  it('sends history on follow-up after clicking a clarification chip', async () => {
    postMock.mockResolvedValueOnce({
      data: {
        status: 'clarification',
        answer: 'I need a little more detail.',
        clarification_questions: ['Gas or electric?'],
        follow_up_required: true,
      },
    })
    postMock.mockResolvedValueOnce({
      data: {
        status: 'ok',
        answer: 'Here is your estimate.',
        estimate: {
          task_code: 'WATER_HEATER_REPLACE_50G_GAS',
          grand_total: 2500,
          subtotal: 2300,
          labor_total: 800,
          materials_total: 1400,
          tax_total: 100,
          markup_total: 0,
          misc_total: 0,
          confidence: 0.92,
          confidence_label: 'HIGH',
          line_items: [],
          assumptions: [],
          market_adjustments: [],
        },
        follow_up_required: false,
      },
    })

    const user = userEvent.setup()
    render(<PublicQuotePage />)

    await user.type(screen.getByPlaceholderText(/Describe the job/i), 'replace water heater')
    await user.click(screen.getByRole('button', { name: /Quote/i }))
    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1))

    const chip = await screen.findByRole('button', { name: 'Gas or electric?' })
    await user.click(chip)

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(2))
    const secondCall = postMock.mock.calls[1][0]
    const secondBody = postMock.mock.calls[1][1]
    expect(secondCall).toBe('/public-agent/quote')
    expect(secondBody.history).toEqual([
      { role: 'user', content: 'replace water heater' },
      { role: 'assistant', content: 'I need a little more detail.' },
      { role: 'user', content: 'Gas or electric?' },
    ])
  })

  it('displays a rich estimate card with line items and confidence', async () => {
    postMock.mockResolvedValue({
      data: {
        status: 'ok',
        answer: 'Typical DFW toilet replacement.',
        task_code: 'TOILET_REPLACE',
        estimate: {
          task_code: 'TOILET_REPLACE',
          grand_total: 750,
          subtotal: 700,
          labor_total: 300,
          materials_total: 400,
          tax_total: 50,
          markup_total: 0,
          misc_total: 0,
          confidence: 0.88,
          confidence_label: 'HIGH',
          line_items: [
            { description: 'Toilet bowl', quantity: 1, unit: 'ea', unit_cost: 250, total_cost: 250, line_type: 'material' },
            { description: 'Labor', quantity: 1.5, unit: 'hr', unit_cost: 100, total_cost: 150, line_type: 'labor' },
          ],
          assumptions: ['First-floor access assumed'],
          market_adjustments: [],
        },
        follow_up_required: false,
      },
    })

    const user = userEvent.setup()
    render(<PublicQuotePage />)

    await user.type(screen.getByPlaceholderText(/Describe the job/i), 'replace toilet')
    await user.click(screen.getByRole('button', { name: /Quote/i }))

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/Typical DFW toilet replacement/i)).toBeInTheDocument()
    expect(screen.getByText('$750.00')).toBeInTheDocument()
    expect(screen.getByText(/Confidence: 88%/i)).toBeInTheDocument()
    expect(screen.getAllByText('Toilet bowl').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Labor').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('First-floor access assumed')).toBeInTheDocument()
  })

  it('shows error message when the API fails', async () => {
    postMock.mockRejectedValue(new Error('Server down'))

    const user = userEvent.setup()
    render(<PublicQuotePage />)

    await user.type(screen.getByPlaceholderText(/Describe the job/i), 'broken pipe')
    await user.click(screen.getByRole('button', { name: /Quote/i }))

    await waitFor(() => expect(postMock).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('Server down')).toBeInTheDocument()
  })
})
