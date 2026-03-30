// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EstimatorRoute from './page'

const pendingWorkspace = new Promise(() => {})

vi.mock('@/components/estimator/EstimatorPage', () => ({
  EstimatorPage: function MockEstimatorPage() {
    throw pendingWorkspace
  },
}))

describe('Estimator route', () => {
  it('shows a loading fallback while the pricing workspace suspends', () => {
    render(<EstimatorRoute />)

    expect(screen.getByText(/loading pricing workspace/i)).toBeInTheDocument()
  })
})
