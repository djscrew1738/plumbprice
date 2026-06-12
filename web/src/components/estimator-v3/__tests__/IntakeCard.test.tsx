import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { IntakeCard } from '../IntakeCard'
import type { IntakeResultV3 } from '@/lib/api-v3'

const mockIntake: IntakeResultV3 = {
  intent: 'toilet_replace',
  fixture_counts: { toilet: 2 },
  location: 'Plano',
  urgency: 'same_day',
  preferred_tier: 'standard',
  confidence: 0.85,
}

describe('IntakeCard', () => {
  it('renders inferred facts', () => {
    render(<IntakeCard intake={mockIntake} onConfirm={vi.fn()} />)
    expect(screen.getByText(/2 Toilets/i)).toBeInTheDocument()
    expect(screen.getByText(/Plano/i)).toBeInTheDocument()
    expect(screen.getByText(/Same_day/i)).toBeInTheDocument()
  })

  it('calls onConfirm when Looks right is clicked', () => {
    const onConfirm = vi.fn()
    render(<IntakeCard intake={mockIntake} onConfirm={onConfirm} />)
    fireEvent.click(screen.getByRole('button', { name: /Looks right/i }))
    expect(onConfirm).toHaveBeenCalledWith(mockIntake)
  })

  it('toggles edit mode', () => {
    render(<IntakeCard intake={mockIntake} onConfirm={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Edit/i }))
    expect(screen.getByLabelText(/Location/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Done editing/i }))
    expect(screen.queryByLabelText(/Location/i)).not.toBeInTheDocument()
  })
})
